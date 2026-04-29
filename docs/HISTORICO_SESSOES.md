# Histórico de sessões — protocolo-ouroboros

> Diário cronológico das sessões maratona. Extraído do CLAUDE.md em 2026-04-29 para manter a constituição enxuta.
> Cada entrada lista entregas-chave, commits e padrões canônicos descobertos. Detalhes operacionais ficam nos `HANDOFF_<data>_*.md` correspondentes.

## 2026-04-28/29 — Onda 0 + Onda 1 fechadas + Onda 2 LLM iniciada (Opus autônomo)

Sessão Opus principal autônoma executando o plan `pure-swinging-mitten`. Atualização incremental conforme cada sprint fecha — preserva progresso se a sessão cair.

**13 sprints fechadas** (em ordem):

| # | Sprint | Commit | Resumo |
|---|--------|--------|--------|
| 1 | ANTI-MIGUE-11 | `1bd52fa` | pin pyvis<1.0 + requirements-lock.txt |
| 2 | ANTI-MIGUE-12 | `d00b10f` | backfill frontmatter `concluida_em` em 165 specs |
| 3 | MAKE-AM-01 | `05b97d2` | `make anti-migue` como entry point único do gauntlet |
| 4 | CI-01 | `3ccd6a3` | CI workflow sem `\|\|` mascarando + smoke + acentuação |
| 5 | ANTI-MIGUE-05 | `e5a3c1a` | teste regressivo idempotência fallback supervisor cupom |
| 6 | DESIGN-01 | `5205ff7` | `docs/BLUEPRINT_VIDA_ADULTA.md` (8 domínios + mermaid) |
| 7 | ANTI-MIGUE-09 | `4580aa0` | teste idempotência end-to-end `--reextrair-tudo` |
| 8 | ANTI-MIGUE-10 | `e7861d4` | `docs/BOOTSTRAP.md` (clone + setup honesto) |
| 9 | ANTI-MIGUE-06 | `c41c12b` | ramificação Sprint 87 (9 retroativas + 8 novas DOC/DASH) |
| 10 | ANTI-MIGUE-08 | `c5f8b5f` | refactor 4 arquivos > 800L (worktree isolado) |
| 11 | ANTI-MIGUE-01 | `c44a8b3` | gate 4-way conformance + `make conformance-<tipo>` |
| 12 | REVISAO-LLM-ONDA-01 | `5e87caa` | reescrita 7 LLM-* sob ADR-13 (sem API anthropic) |
| 13 | LLM-01-V2 | `bc42a6b` | template proposta + supervisor_contexto + `_rejeitadas/` |
| 14 | LLM-02-V2 | `30da12f` | skill `/propor-extrator` + script gerador + exemplo pix_foto_comprovante |
| 15 | LLM-04-V2 | `f091558` | skill `/auditar-cobertura` + script Python + relatório runtime real |
| 16 | META-SUPERVISOR-01 | `<próximo>` | doc canônico `SUPERVISOR_OPUS.md` + bloco padrão em 30 specs + arquivamento Sprint 34/36 |

**Achados colaterais formalizados** (zero TODO solto): 9 sub-sprints retroativas Sprint 87.x, 8 novas (DOC-21..26, DASH-02/03), 7 LLM-*-V2 reescritas, 1 fix-test-busca-índice (teste frágil revelado pelo refactor).

**Métricas finais**:
- pytest: 2037 collected baseline → **2053 collected** (+16). 2043 passed, 9 skipped, 1 xfailed.
- Arquivos > 800L: 4 → **0**.
- Smoke: 10/10 contratos OK.
- Lint: exit 0.
- Specs concluídas com frontmatter `concluida_em`: 187/187 (100%).

**Padrões canônicos novos** registrados em VALIDATOR_BRIEF rodapé:
- `(aa)` Gate 4-way operacional via `make conformance-<tipo>`.
- `(bb)` Refactor de arquivos > 800L: extração de cluster coeso + re-export para retrocompat.
- `(cc)` Refactor revela teste frágil: refactor que aperta correção pode expor bug pré-existente — abrir sprint-filha e seguir.

**Achado-bloqueio em ANTI-MIGUE-08**: 2 testes de busca passavam por acidente em main (dependiam de grafo de produção real). Sprint-filha `sprint_fix_test_busca_indice_fragil` formaliza fix correto.

Próximas sprints prováveis: LLM-02-V2 (skill `/propor-extrator`), LLM-04-V2 (skill `/auditar-cobertura`), LLM-03-V2 (proposição de regra de categoria).

## 2026-04-29 — Auditoria 4-way self-driven + brainstorming de redesign

Sessão Opus principal sem dispatch de subagents. Foco duplo:
1. Estender o Revisor para comparação 4-way ETL × Opus × Grafo × Humano.
2. Auditoria interna identificando 15 achados em A/B/C/D, gerando 9 sprints corretivas AUDIT2-*.

Entregas runtime:
- `transcricoes_v2.json`: 27 → 60 entries.
- `decisoes_opus_v2.json`: novo, 60 decisões.
- `revisao_humana.sqlite`: 145 → 430 marcações.
- Coluna `valor_grafo_real` populada via `popular_valor_grafo_real.py`.
- pytest baseline: 1.971 → **1.987 passed**.
- CSV ground-truth: 8 → 11 colunas.
- Dashboard Revisor: 3 → 4 linhas (ETL/Opus/Grafo/Humano) com flags de divergência.

Sprints AUDIT2 fechadas em sequência: SPRINT107-RETROATIVA, PATH-RELATIVO-COMPLETO, REVISAO-LIMPEZA-OBSOLETOS, METADATA-PESSOA-CANONICA, RAZAO-SOCIAL-HOLERITE, METADATA-ITENS-LISTA. Pendentes (formalizadas em backlog): FORNECEDOR-CAPITALIZACAO, DAS-DATA-ANTIGA-BACKFILL, ENVELOPE-VS-PESSOA-CANONICO.

No fim da sessão (segundo bloco) foi feito brainstorming de redesign estratégico que produziu o plano `pure-swinging-mitten.md` em `~/.claude/plans/`: auditoria honesta com 46 falhas identificadas + plano de fechamento em 6 ondas (~170h). O plano materializa a visão "Central de Vida Adulta" prevista em ADR-21.

## 2026-04-28 — Automações Opus (Sprint 103 fase Opus + 7 sprints + 1 sub-sprint)

A fase Opus da Sprint 103 entregou 5 achados materiais que viraram automações individuais. Sprint 108 amarrou todas em fluxos canônicos do `run.sh`, eliminando operação manual recorrente.

| Sprint | Commit | Achado runtime real |
|---|---|---|
| 103 (fase Opus) | `6009b00` | 29 pendências com transcrição + 145 valor_opus persistidos; 44 divergências ETL × Opus mapeadas; UI Revisor 3-colunas |
| INFRA-DEDUP-CLASSIFICAR | `598e723` | 3 → 1 PDF (-2 fósseis Americanas) |
| 98a | `6228c91` | 24 paths quebrados → 0 (todos os holerites pós-Sprint 98) |
| 105 | `ab9d5de` | 6 → 3 arquivos casal/ (-3 migrados para andre/ via CPF) |
| 107 | `b470024` | DAS PARCSN → RECEITA_FEDERAL codificado |
| 106 | `a05ebdb` | Motor de fallback similar ativo (phash + temporal + textual) |
| 108 | `18a58d8` | 3 automações encadeadas em --full-cycle e --reextrair-tudo |
| 106a | `59bc381` | Critério composite (palavras PT-BR + ratio non-letras): 2/2 cupons-foto detectados como ilegíveis |

Padrões canônicos novos formalizados em VALIDATOR_BRIEF rodapé:
- (q) **Automação no fluxo canônico OU não está resolvida**.
- (r) **Fornecedor sintético para entidades fiscais** (`mappings/fornecedores_sinteticos.yaml`).
- (s) **Critério de legibilidade composite** (chars úteis + palavras PT-BR + ratio non-letras).
- (t) **Backfill heurístico por mes_ref + razao_social + valor**.

## 2026-04-27 — Cluster UX v1+v2+v3 (17 sprints + INFRA-CONSOLIDA-V2)

Rodada cluster UX com 17 sprints + 1 INFRA. Renomeação de clusters: "Hoje" → "Home" (UX-121), "Dinheiro" → "Finanças" (UX-125). Aliases backward-compat preservados. UX-126 introduziu nomes humanizados em Catálogo via `mappings/tipos_documento_humanizado.yaml` (37 tipos). Baseline pytest cresceu para 1.839 passed.

Sprints concluídas em sequência: ver `docs/HANDOFF_2026-04-27_cluster_UX.md` para detalhes.

## 2026-04-26/27 — Fase NU completa + P1 98+101 + 98-1

Total 16+ commits, 1 worktree por sprint (todos cleanup ao final). pytest 1.530 → 1.620 (+90, zero regressão). Lint verde, smoke 8/8 em cada passo.

| # | Evento | Commit |
|---|--------|--------|
| 1 | Sprint 95 (linking runtime) | `2df40ae` — 0 → 23 arestas `documento_de` |
| 2 | Sprint 96 (classifier robusto cupons curtos) | `9befcb5` — `inbox/1.jpeg` agora classifica `cupom_fiscal_foto/ocr_curto` |
| 3 | Sprint D2 (revisor visual Streamlit) | `b3026a7` — substitui Sprint AUDITORIA-ARTESANAL-FINAL |
| 4 | Sprint 97 (page-split heterogêneo) | `22c9e5e` — predicado por classificação + branch reversível |
| 5 | Sprint 90a (inbox detecta holerite) | `b8ab3fe` — defesa em duas camadas |
| 6 | Sprint 90b (DAS PARCSN drift) | `c136ea6` — 10 → 19 nodes; causa real era regex sem `ç` |
| 7 | Sprint 101 (`./run.sh --full-cycle`) | `d615488` |
| 8 | Sprint 98 (renomeação retroativa) | `835f0a7` (script) + `a48b843` (`--executar`) — 121/121 ações, -97 PDFs fósseis, +24 holerites canônicos |
| 9 | Sprint 98-1 (P2 diagnóstica) | `84b071e` — engine de envelope confirmada íntegra |

Padrões canônicos novos:
1. **Disciplina de worktree** — prefixar `cd "$WORKTREE_PATH"` em todo Bash.
2. **Hipótese da spec não é dogma** — diagnóstico empírico antes de codar.
3. **Subregra composta retrocompatível** — schema YAML `regras: [{tipo, requer_todos, requer_qualquer, ocr_minimo, ocr_maximo}]`.
4. **Branch reversível** — page-split tentativo com reversão se homogêneo.
5. **Defesa em duas camadas** — fix YAML + pre-check Python.
6. **PII em revisor visual** — mascarar em UI, JSON, observação humana E relatório final.

## 2026-04-26 (primeira parte) — Auditoria geral

Auditoria de fim-de-rota com plan mode aprovado. 2 agentes Opus em background (vault + ETL).

Artefatos criados: `docs/AUDITORIA_2026-04-26.md`, `docs/auditoria_etl_2026-04-26.md`, `docs/auditoria_vault_2026-04-26.md`, `docs/adr/ADR-21-fusao-ouroboros-controle-bordo.md`, 10 specs novas em backlog/.

Achados P0 inéditos: 0% documentos vinculados em runtime, classifier silencioso ignora NF imagem-only, PDF heterogêneo acumula em `_classificar/`, 13 holerites G4F mal classificados, DAS PARCSN drift -47%.

Achado de produto: reserva de emergência atingida 100% (R$ 44.019,78 / R$ 27.000,00).

Sprint substituída: AUDITORIA-ARTESANAL-FINAL → Sprint D2 (revisor visual Streamlit).

## 2026-04-24 — Rota longa (9 sprints + handoff)

30+ commits em main. Baseline pytest 1.261 → 1.530 (+269). Zero regressão. Smoke 8/8 preservado.

Bloco 1 (cobertura+fidelidade bancária) + Bloco 2 (UX) + Bloco 3 (conta-espelho cartão).

Entregas-chave: 87e (registrar boleto_pdf), F (testes extratores bancários +102), 93a/b/c (flags --deduplicado/--com-ofx/--ignorar-ti, rotulagem Nubank PJ), 92a (4 fixes cirúrgicos + 4 majors), 92b (5 clusters + ADR-22), 92c (design system + 11 SVGs Feather), 82b (conta-espelho cartão).

Sprints 93f + 93g (visibilidade PJ Vitória restaurada): Vitória 575 → **3.160 tx** (PJ 0→828, PF 0→1.757); valor PJ R$ 169.131,13.

## 2026-04-23 — Rota "conserta tudo" + Fases A+B+C+E

Sessão maratona de 19 sprints + 1 sprint de auditoria. 30+ commits em main. 111 testes novos, +122 no total (1.139 → 1.261).

Fases: rota "conserta tudo" (9 sprints), Fase A ressalvas (3), Fase B ZETA (3), Fase C backlog formal (3 em paralelo via worktree), Fase E auditoria técnica.

## 2026-04-22 — Caminho crítico IOTA + KAPPA concluído

Sessão única de orquestração supervisionada: 14 commits, gauntlet verde em cada passo. Sprints 68b–79 + 80 + 81 fechadas. Detalhes em commit `3ac3f41..0a39938`.

Padrões canônicos estabelecidos:
1. **Integração com sistema vivo** (Sprint 70, ADR-18) — adapter em `src/integrations/`.
2. **Soberania do usuário** (Sprint 71) — nota sem tag `#sincronizado-automaticamente` é preservada.
3. **Drill-down canônico** (Sprint 73) — helper `aplicar_drilldown` com debounce por hash.
4. **Chaves de session_state separadas por namespace** (Sprint 77) — `filtro_*` vs `avancado_*`.
5. **Tipagem semântica de edges** (Sprint 74) — `tipo_edge_semantico` em `evidencia`.
6. **Graceful degradation visual** (Sprint 78) — pyvis com placeholder se import falha.
7. **Ressalva = sprint-nova** (anti-débito) — toda ressalva vira item em sprint formal.

## Sessões anteriores

Sessões anteriores a 2026-04-22 estão documentadas nos `HANDOFF_*` correspondentes em `docs/`. Ver também `docs/AUDITORIA_SPRINTS.md` para auditoria sincera de cada sprint 1-30.

---

*"O que esquecemos volta como armadilha. O que registramos volta como padrão." — princípio do snapshot honesto*
