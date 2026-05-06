# ESTADO_ATUAL.md -- Snapshot tecnico em 2026-05-06 (pos-Onda T fechada, Onda M especificada)

> **Versionado a partir de 2026-04-29 pela Sprint DOC-VERDADE-01.A; atualizado em 2026-05-06 com Onda M (modularização) especificada**.
> Whitelist em `.gitignore` permite este arquivo + COMO_AGIR.md no repo (POR_QUE.md e PROMPT_NOVA_SESSAO.md continuam locais por conter PII estrutural).
> Esta doc e fotografia do momento — para verdade vivo consulte `git log` + `ls docs/sprints/concluidos/`.
> Para auditar este snapshot contra realidade: `python scripts/auditar_estado.py`.

## Sessao 2026-05-06 (parte 2) -- Onda M especificada (modularização do dashboard)

Após Onda T+Q+U fecharem em 2026-05-06 (29 sprints UX-T-* + 3 UX-Q-* + 4 UX-U-* + ressalvas), revisão visual do dono em 2026-05-06 expôs problemas estruturais na arquitetura CSS/componentes do dashboard:

- **17 páginas com `_CSS_LOCAL_*`** (50-300 linhas inline cada).
- **`tema_css.py` com 1675 linhas** de CSS hard-coded em Python.
- **`instalar_fix_sidebar_padding` com 211 linhas e 56 `setProperty`** afetando TODAS as páginas globalmente.
- **17 funções HTML helpers em `tema.py`** (9 são componentes, 8 utilitários — espalhados).
- **4 páginas com duplicação de header** (`hero_titulo_html` + `_page_header_html`) — corrigidas em commit `2817706`.

**Causa identificada**: commit `928628c` ("topbar polish") aplicou regras JS universais que bagunçaram layouts internos de páginas como Busca Global e Extração Tripla — revertido em `2817706`.

**Decisão (dono, 2026-05-06)**: criar Onda M (modularização real) ANTES de continuar com mais sprints visuais.

**Onda M — 4 sprints + 4 sub-sprints** (commit `4b62b0b`):
- **UX-M-01** — Tokens CSS centralizados (copiar `novo-mockup/_shared/tokens.css`).
- **UX-M-02** — Componentes universais HTML (consolidar em `ui.py`).
- **UX-M-03** — CSS canônico do mockup (copiar `novo-mockup/_shared/components.css`).
- **UX-M-04** — Shell consolidado em CSS estático (211→80 linhas, 56→10 setProperty).
- **UX-M-02.A..D** — Migração de 30+ páginas em 4 clusters (paralelo).

**Esforço total**: 36-44h. Detalhes em `docs/sprints/backlog/INDICE_ONDA_M_MODULARIZACAO.md`.

**Sprint UX-M-AUDITORIA** (2026-05-06, plano `auditoria-honesta-da-magical-lovelace.md`): refinou as 4 specs para alinhar com realidade do código (descobriu que `instalar_fix_sidebar_padding` tem 211 linhas, não 120; mockup já tem `tokens.css`/`components.css` canônicos; 17 helpers em `tema.py`); criou `VALIDATOR_BRIEF.md` (faltava); atualizou 7 docs canônicos.

**Próximo passo**: dono valida specs Onda M endurecidas; ao aprovar, executor começa por UX-M-01 ou UX-M-04 (paralelos).

---

## Sessao 2026-05-06 (parte 1) -- Reorganização por tela (Onda U+T+Q vigente, Fase Corretiva arquivada)

Após executar as 14 sprints UX-RD-FIX-01..14 em 2026-05-05 (gauntlet verde, métricas DOM passaram), uma revisão visual em 2026-05-06 mostrou que **a percepção integrada continua quebrada**: sidebar mistura widgets antigos (logo escudo, Granularidade/Mês/Pessoa selectbox, Busca Global text input) com shell HTML novo; KPIs semantica errados na Home (financeiros vs agentic-first do mockup); layout esparso; bugs Plotly "undefined".

**Diagnóstico arquitetural** (Explore agent + leitura `app.py:206-364`):
- `_sidebar()` faz dois shells concorrentes: emite `renderizar_sidebar()` HTML novo E DEPOIS injeta logo+caption+4 selectbox+text_input.
- Tupla `(periodo, pessoa, granularidade, cluster)` retornada para 29 páginas força filtros globais. Mockup pede filtros inline por página.
- 14 fixes transversais cada um corrigia detalhe em N páginas; bagunça acumulou.

**Decisão (dono)**: arquivar Fase Corretiva (specs UX-RD-FIX-* movidas para `docs/sprints/arquivadas/2026-05-tentativa-fix-transversal/`; código permanece). Adotar **abordagem por tela**:
- **Onda U** (4 sprints estruturantes): U-01 sidebar canônica scroll, U-02 topbar com slot ações, U-03 page-header canônico, U-04 filtros por página + sidebar shell-only.
- **Onda T** (29 sprints): UMA tela inteira por sprint -- layout 1:1 mockup + funcional + dados reais + validação humana.
- **Onda Q** (3 sprints): auditoria visual completa + regressão funcional + fechamento.
- **Total**: 36 sprints em ~5-6 semanas.

Roteiro canônico: `docs/sprints/backlog/ROTEIRO_TELAS_2026-05-06.md`. Plano operacional: `~/.claude/plans/auditoria-honesta-da-magical-lovelace.md`.

**Garantias para confiança**: validação humana obrigatória entre cada sprint; captura side-by-side mockup × dashboard automática; reversibilidade (commits isolados); validador integrador (Opus interativo) revisa cada output; quality gates por onda.

**Próximo passo**: dono valida ROTEIRO + 4 specs Onda U; ao aprovar U-01, executor começa com captura BEFORE.

---

## Sessao 2026-05-05 -- Auditoria honesta da reforma de UI + 14 sprints corretivas

Branch `ux/redesign-v1` fechou 19 sprints UX-RD-01..19 em 2026-05-04 (todas marcadas concluida). Auditoria independente em 2026-05-05 (Opus principal interativo) revelou:

- **Score real 64/100** (vs meta 95+). Detalhe em `docs/auditorias/AUDITORIA_REDESIGN_2026-05-05.md`.
- **13 divergencias** ainda abertas: 5 telas Bem-estar inacessiveis por deep-link, 5 abas-fantasma duplicando 2 paginas, bug Despesa R$ 0 no Extrato, lint quebrado (11 .md), iconografia 0% portada (0/52 glyphs SVG do `glyphs.js`), tipografia escala-grossa (config.toml `font="monospace"` vaza Source Code Pro), Plotly modebar visivel + paleta nao-Dracula, Material Symbols vazando como texto bruto ("keyboard_double_arrow_left"), h1 duplicado (`st.title` global + page-title), 60 .py sem citacao filosofica, kpi-grid 220px (mockup pede 180), breadcrumb nao-clicavel (`<span>` em vez de `<a>`), skip-links + aria-current ausentes.
- **Decisao arquitetural** confirmada pelo dono: **Decisao A** — criar 5 paginas Bem-estar reais (Treinos, Marcos, Alarmes, Contadores, Tarefas). FIX-14 cobre as 5 orfas (Memorias, Rotina, Cruzamentos, Privacidade, Editor TOML) via deep-link interno `?secao=`.
- **14 sprints corretivas** redigidas em `docs/sprints/backlog/sprint_ux_rd_fix_01..14.md` + roteiro mestre `ROTEIRO_REDESIGN_FINAL.md`.

Pytest baseline pos-redesign: **2.520 passed / 9 skipped / 1 xfailed** (validado 2026-05-05). Smoke 10/10. Lint exit 1 (FIX-01 corrige).

XLSX consolidado real: `data/output/ouroboros_2026.xlsx` (nao `extrato_consolidado.xlsx` como CLAUDE.md menciona — divergencia documental pequena).

Linha de montagem das 14: ~7-8 dias uteis. Onda C1 (FIX-01..06) paralelizavel; C2 (FIX-07..09) paralelizavel; C3 (FIX-10) bloqueia C4 (FIX-11) e C5 (FIX-14); FIX-13 sempre ULTIMA.

---


## Versao + saude geral

```
VERSAO: 5.11 | STATUS: PRODUCAO + AUDITORIA HONESTA 46 ACHADOS (plan pure-swinging-mitten aprovado 2026-04-29) | LANG: PT-BR
TRANSACOES: 6.094 | MESES: 82 (out/2019 a out/2026) | BANCOS: 6 | EXTRATORES: 22
GRAFO: 7.494+ nodes + 24.732+ edges. 24 paths arquivo_origem corrigidos pela Sprint 98a.
TESTES: 2.018 passed / 9 skipped / 1 xfailed (baseline real medida com pytest --collect-only -- doc anterior dizia 1.987, delta de +31 testes nao registrados)
SMOKE: 8/8 contratos aritmeticos OK (declarado; auditoria revelou que so 6 estao realmente implementados; sprint ANTI-MIGUE-04 fecha o gap)
LINT: exit 0 (zero violacoes)
DASHBOARD: Revisor com 4-colunas ETL/Opus/Grafo/Humano + flags divergencia tipo A/B + export CSV 11 colunas
RUNTIME LIMPO: data/raw/_classificar/ 3->1 PDF | data/raw/casal/ 6->3 (3 migrados via CPF) | 24/24 holerites com path correto no grafo
GROUND-TRUTH: 60 entries em transcricoes_v2.json (+33 vs Sprint 103); 430 marcacoes (200 com valor_grafo_real)
PLANO ATIVO: ~/.claude/plans/pure-swinging-mitten.md (auditoria + 6 ondas de fechamento ~170h)
```

## Sessao 2026-04-29 (segunda parte) -- brainstorming de redesign

Foco: responder "o que falta pro projeto estar finalizado". 3 agentes Explore em paralelo + sintese honesta. Resultado:

- **46 falhas reais identificadas** com arquivo:linha (9 P0 + 13 P1 + 15 P2 + 9 P3).
- **Plano de fechamento em 6 ondas** (~170h): Onda 1 anti-migue + restaurar debitos, Onda 2 ADR-08 supervisor Opus interativo (LLM-*-V2 reescrito sob ADR-13, sem API anthropic), Onda 3 cobertura documental universal, Onda 4 cruzamento micro + IRPF, Onda 5 mobile bridge + fontes adicionais, Onda 6 UX/UI + OMEGA.
- **CLAUDE.md simplificado** de 640 para ~250 linhas. Historico de sessoes movido para `docs/HISTORICO_SESSOES.md`.
- **Diagnostico de testes**: 2.018 passed (real) vs 1.987 (doc). Zero testes fantasma; doc apenas desatualizada.

Referencias:
- Plano completo: `~/.claude/plans/pure-swinging-mitten.md`
- Auditoria self anterior: `docs/AUDITORIA_2026-04-29_self.md`

## Sessao 2026-04-29 -- auditoria 4-way self-driven

Sessao supervisor Opus principal sem dispatch de subagents. Foco duplo:
(1) extender o Revisor para comparacao 4-way ETL x Opus x Grafo x Humano;
(2) auditoria interna identificando 15 achados classificados em A/B/C/D.

### Entregas runtime

| Artefato | Antes | Depois |
|---|---|---|
| transcricoes_v2.json | 27 entries | **60 entries** (+33 via flag --estender) |
| decisoes_opus_v2.json | inexistente | **60 decisoes** geradas via classificacao por familia |
| revisao_humana.sqlite marcacoes | 145 | **430** (+285) |
| Coluna valor_grafo_real | inexistente | **populada via popular_valor_grafo_real.py** |
| pytest baseline | 1.971 | **1.987** (+16: 11 novos test_revisor_4way + 5 atualizacao) |
| CSV ground-truth header | 8 colunas | **11 colunas** (3 flags divergencia tipo A/B) |
| Dashboard Revisor | 3 linhas por dim | **4 linhas (ETL/Opus/Grafo/Humano)** com marcadores |

### Sprints corretivas geradas (9 backlog AUDIT2-*)

Documentadas em `docs/AUDITORIA_2026-04-29_self.md`. Tier 1 do
ESTADO_ATUAL.md atualizado com a nova fila.

## Sessao 2026-04-28 -- automacoes Opus (7 sprints + 1 sub-sprint)

A fase Opus da Sprint 103 entregou 5 achados materiais que viraram automacoes
individuais. Sprint 108 amarra todas em fluxos canonicos do `run.sh`,
eliminando operacao manual recorrente.

### Sprints concluidas em sequencia

| Sprint | Commit | Achado runtime real |
|---|---|---|
| **103 (fase Opus)** | `6009b00` | 29 pendencias com transcricao + 145 valor_opus persistidos; 44 divergencias ETL x Opus mapeadas; UI Revisor 3-colunas |
| **INFRA-DEDUP-CLASSIFICAR** | `598e723` | 3 -> 1 PDF (-2 fosseis Americanas, sha 6c1cc203...) |
| **98a** | `6228c91` | 24 paths quebrados -> 0 (todos os holerites pos-Sprint 98) |
| **105** | `ab9d5de` | 6 -> 3 arquivos casal/ (-3 migrados para andre/ via CPF) |
| **107** | `b470024` | DAS PARCSN -> RECEITA_FEDERAL codificado (migra na proxima reextracao) |
| **106** | `a05ebdb` | motor de fallback similar ativo (phash + temporal + textual) |
| **108** | `18a58d8` | 3 automacoes encadeadas em --full-cycle e --reextrair-tudo |
| **106a** | `59bc381` | criterio composite (palavras PT-BR + ratio non-letras): 2/2 cupons-foto detectados como ilegiveis |

### Padroes canonicos novos (formalizar em VALIDATOR_BRIEF rodape)

(q) **Automacao no fluxo canonico OU nao esta resolvida**: lições da fase Opus que viram operacao manual repetida sao falsas conclusoes. Sprint 108 (run_passo helper) e o ponto que transforma achado em invariante.

(r) **Fornecedor sintetico para entidades fiscais**: `mappings/fornecedores_sinteticos.yaml` declara RECEITA_FEDERAL/INSS com CNPJ oficial; documentos casam por tipo_documento. Contribuinte preservado em `metadata.contribuinte` para auditoria.

(s) **Criterio de legibilidade composite**: chars uteis + palavras conhecidas em PT-BR + ratio non-letras. Whitelist domínio-especifica (zero preposicoes curtas que aparecem por acaso em garbage Tesseract).

(t) **Backfill heuristico por mes_ref + razao_social + valor**: paths quebrados pos-rename retroativo sao recuperaveis via metadata em vez de rerodar pipeline inteiro.

## Fase NU concluida (rodada 2026-04-26/27, ja em ESTADO anterior)

(arquivada na secao historica deste arquivo + handoff anterior)

## P1/P2 ainda pendentes (sessao futura)

- **Sprint 99** (P1, ~1h) -- redactor PII em logs INFO. **Status: ja em main** (commit anterior).
- **Sprint 100** (P1, ~2h) -- deep-link tab. **Status: CONCLUIDA** (commit `5614da9`).

## P3 backlog (16 specs em backlog, todas nao-bloqueantes)

```
sprint_102_pagador_vs_beneficiario.md
sprint_24_automacao_bancaria.md
sprint_25_pacote_irpf.md
sprint_27b_grafo_motores_avancados.md
sprint_34_supervisor_auditor.md
sprint_36_metricas_ia_dashboard.md
sprint_83_rename_protocolo_ouroboros.md
sprint_84_schema_er_relacional_visual.md
sprint_85_xlsx_docs_faltantes_expandido.md
sprint_86_ressalvas_humano_checklist.md
sprint_93d_preservacao_forte_downloads.md
sprint_93e_coluna_arquivo_origem_xlsx.md
sprint_93h_limpeza_clones_andre.md
sprint_94_fusao_total_vault_ouroboros.md
sprint_Fa_ofx_duplicacao_accounts.md
sprint_INFRA_PII_HISTORY.md
```

## Sessao humana pendente

- **Revisao via Revisor (Sprint D2 + 103)** -- 27 pendencias atuais, ~3-4h sessao Opus + supervisor par-a-par. Pre-requisito antes de OMEGA. NAO eh sprint-executor; eh sessao humana com Opus de apoio.

## Fase OMEGA (estrategica, 12-18 meses)

Sprint 94a-f desbloqueada por ADR-21:
- 94a Saude (receitas, exames, planos)
- 94b Identidade (RG, CNH, passaporte)
- 94c Vida profissional (contratos, registrato, rescisao)
- 94d Vida academica (historico, diplomas)
- 94e Busca global cross-dominio
- 94f Obsidian mobile sync

Pre-requisitos: P1 fechadas (todas em main) + sessao humana de validacao via Revisor + reextracao em volume com fornecedor sintetico + criterio legibilidade refinado.

## Numeros (delta sessao automacoes Opus)

| Metrica | Antes (`5614da9`) | Depois (`59bc381`) |
|---|---|---|
| pytest | 1.917 | **1.971** (+54 testes) |
| Sprints concluidas | 113 | **122** (+9: INFRA-DEDUP, 98a, 105, 106, 106a, 107, 108, 100, 103-fase-Opus) |
| Pendencias do Revisor | 29 | 27 (-2 dedup) |
| Paths quebrados grafo | 24 | 0 |
| Arquivos em data/raw/_classificar/ | 3 | 1 |
| Arquivos em data/raw/casal/ | 6 | 3 (-3 via CPF) |
| Lint exit code | 0 | 0 |
| Linhas de codigo Python (src/) | ~30k | ~33k (+3k: dedup, backfill, ocr_fallback, etc.) |

## Saude inviolaveis (mantidas)

- Pipeline ETL maduro: 22 extratores (9 bancarios + 13 documentais).
- Categorizacao: 100% (111 regras + overrides).
- Smoke aritmetico 8/8 desde Sprint 56.
- Holerites G4F + Infobase: 24/24 nodes corretos com paths atualizados.
- Itau CC: 100% fidelidade centavo-a-centavo.
- Vault Obsidian: sync ativo via `sync_rico` em `Pessoal/Casal/Financeiro/`.
- Reserva de emergencia: 100% atingida (R$ 44.019,78 / R$ 27.000,00).

## Comandos canonicos (atualizados pos-Sprint 108)

| Comando | Uso |
|---------|-----|
| `make smoke` | Health check + 8 contratos aritmeticos. <10s. |
| `make lint` | ruff + acentuacao. |
| `.venv/bin/pytest tests/ -q` | Suite completa (~40s). Esperado: 1.971+. |
| `./run.sh --check` | 23 checagens de ambiente. |
| `./run.sh --inbox` | Processa inbox e _classificar/. |
| `./run.sh --tudo` | Pipeline completo. |
| `./run.sh --full-cycle` | inbox + 3 automacoes Opus + tudo (Sprint 101+108). |
| `./run.sh --reextrair-tudo` | confirmacao + 3 automacoes + reprocessar com --forcar (Sprint 104+108). |
| `./run.sh --dashboard` | Streamlit dashboard. |
| Menu opcao 7 | Auditoria Opus completa (delega --reextrair-tudo). |
| `tail logs/auditoria_opus.log` | Inicio/fim/duracao de cada automacao. |

## Automacoes Opus (Sprint 108 -- detalhe)

```
[passo 0] inbox processing                                 (--inbox)
[passo 1] dedup_classificar_lote --executar                # INFRA-DEDUP
[passo 2] migrar_pessoa_via_cpf --executar                 # Sprint 105
[passo 3] backfill_arquivo_origem_lote --executar          # Sprint 98a
[passo 4] python -m src.pipeline --tudo                    # gera XLSX, relatorios
```

Doc completo: `docs/AUTOMACOES_OPUS.md`.

Sprint 106 (OCR fallback similar) **nao** esta encadeada por padrao -- pode ser invocada manualmente:
```bash
.venv/bin/python -m src.intake.ocr_fallback_similar --reanalisar-conferir --executar
```

## Estado git

- Branch: `main`
- Ultimo commit: `59bc381` (Sprint 106a -- criterio legibilidade composite)
- Push status: tudo sincronizado com origin/main.
- Worktrees: limpos.

## Ordem de execucao recomendada para proxima sessao

### Tier 0 -- Onda 1 do plano pure-swinging-mitten (2026-04-29)

Onda anti-migue + restaurar debitos. Bloqueante para Onda 2-6.
Detalhes completos em `~/.claude/plans/pure-swinging-mitten.md`.

**Atualizado em 2026-04-29 pela Sprint DOC-VERDADE-01.A (auditoria contra realidade)**:

```
[CONCLUIDA c5cdac88] ANTI-MIGUE-03 (diagnostico de testes 1.987 vs 2.018)
[CONCLUIDA c5cdac88] ANTI-MIGUE-07 (sincronizar CLAUDE/ESTADO/PROMPT)
[CONCLUIDA c5cdac88] ANTI-MIGUE-04 (smoke aritmetico 6 -> 10 contratos -- ja em main)
[CONCLUIDA c5cdac88] ANTI-MIGUE-02 (anti_orfao.py implementado e integrado em --full-cycle via Sprint 108)
[VERIFICADO]         Backlog ja tem 82 specs (meta de ~50 superada)
[CONCLUIDA c44a8b3]  ANTI-MIGUE-01 (gate 4-way conformance + make conformance-<tipo>)
[CONCLUIDA e5a3c1a]  ANTI-MIGUE-05 (UUID -> hash deterministico em fallback supervisor cupom)
[CONCLUIDA c41c12b]  ANTI-MIGUE-06 (Sprint 87 ramificada em 9 retroativas + 8 novas DOC/DASH)
[CONCLUIDA c5f8b5f]  ANTI-MIGUE-08 (refactor 4 arquivos > 800L: tema, dados, revisor, ingestor)
[CONCLUIDA 4580aa0]  ANTI-MIGUE-09 (teste idempotencia --reextrair-tudo end-to-end)
[CONCLUIDA e7861d4]  ANTI-MIGUE-10 (docs/BOOTSTRAP.md)
[CONCLUIDA 1bd52fa]  ANTI-MIGUE-11 (pin pyvis<1.0 + requirements-lock.txt)
[CONCLUIDA d00b10f]  ANTI-MIGUE-12 (frontmatter concluida_em em 165 specs concluidas)
```

**Onda 1 fechada integralmente.** Onda 2 (LLM-*-V2) tambem em curso: 3 fechadas
(LLM-01-V2 bc42a6b, LLM-02-V2 30da12f, LLM-04-V2 f091558), 4 restantes em
backlog. Para auditar este snapshot contra estado real: `python scripts/auditar_estado.py`.

### Tier 1 -- Sprints AUDIT2-* (auditoria self-driven 2026-04-29, ~10h total)

A auditoria 4-way da sessao 2026-04-29 detectou 9 sprints corretivas sobre
divergencias ETL/Opus/Grafo. Listadas por prioridade + dependencia.
Sprints AUDIT-* da auditoria externa 2026-04-28 estao **TODAS CONCLUIDAS**
(commits b369bc5 e ancestrais). Detalhes em `docs/AUDITORIA_2026-04-29_self.md`.

```
[P1] ~1h     AUDIT2-SPRINT107-RETROATIVA
             -> backfill fornecedor sintetico em 14 nodes DAS pre-Sprint 107
             -> sem dependencias
[P1] ~1h     AUDIT2-PATH-RELATIVO-COMPLETO
             -> aplicar to_relativo em DAS+boletos+envelopes (era so holerite)
             -> 36 nodes ainda com path absoluto
[P2] ~30min  AUDIT2-FORNECEDOR-CAPITALIZACAO
             -> cupom termico/garantia gravam razao_social UPPERCASE
             -> sem dependencias
[P2] ~30min  AUDIT2-REVISAO-LIMPEZA-OBSOLETOS
             -> remover 23 item_ids node_<id> orfaos pos-reextracao
             -> encadeada em --reextrair-tudo
[P2] ~1h     AUDIT2-RAZAO-SOCIAL-HOLERITE
             -> mapping G4F -> "G4F SOLUCOES CORPORATIVAS LTDA"
             -> sem dependencias
[P2] ~1.5h   AUDIT2-METADATA-PESSOA-CANONICA
             -> gravar metadata.pessoa via pessoa_detector no ingestor
             -> sem dependencias
[P2] ~2h     AUDIT2-DAS-DATA-ANTIGA-BACKFILL
             -> recompor data_emissao de DAS pre-Sprint 90b (periodo Diversos)
             -> dependencia: facilitada por AUDIT2-SPRINT107 rodar antes
[P3] ~4h     AUDIT2-METADATA-ITENS-LISTA
             -> persistir array de itens granular em NFC-e + holerites
             -> impacta dimensao itens da auditoria 4-way
[P3] ~1h     AUDIT2-ENVELOPE-VS-PESSOA-CANONICO
             -> ADR para escolher entre envelope ou pessoa como path canonico
             -> decisao arquitetural com supervisor humano
```

### Tier 2 -- Validacao humana (sessao dedicada)

```
[Sessao humana] -- 27 pendencias no Revisor (3-colunas ETL/Opus/Humano)
  - ./run.sh --dashboard -> cluster Documentos -> aba Revisor
  - Marcar cada par (item, dimensao) como OK/Erro/N-A
  - Botao "Exportar ground-truth CSV" gera dataset para metricas
```

### Tier 3 -- Backlog historico (16 P3 nao-bloqueantes)

```
- Sprint 102 (pagador vs beneficiario IRPF)
- Sprint 25 (pacote IRPF completo)
- Sprint 24 (automacao bancaria)
- Sprint 27b (grafo motores avancados)
- Sprint 36 (metricas IA dashboard)
- Sprint 83 (rename projeto)
- Sprint 84 (schema ER relacional visual)
- Sprint 85 (XLSX docs faltantes expandido)
- Sprint 86 (ressalvas humano checklist)
- Sprint 93d (preservacao forte downloads)
- Sprint 93e (coluna arquivo_origem XLSX)
- Sprint 93h (limpeza clones Andre)
- Sprint 94 (fusao total vault Ouroboros)
- Sprint Fa (OFX duplicacao accounts)
- Sprint INFRA-PII-HISTORY
- Sprint 34 (supervisor auditor)
```

### Tier 4 -- Rota OMEGA (estrategica 12-18 meses)

```
- 94a Saude (receitas, exames, planos)
- 94b Identidade (RG, CNH, passaporte)
- 94c Vida profissional (contratos, registrato, rescisao)
- 94d Vida academica (historico, diplomas)
- 94e Busca global cross-dominio
- 94f Obsidian mobile sync
```

Pre-requisitos OMEGA: Tier 1 fechado + sessao humana de validacao via Revisor + reextracao em volume com fornecedor sintetico estabilizado.

## Auditoria externa (em andamento 2026-04-28)

Ver `docs/AUDITORIA_2026-04-28_externa.md` quando disponivel -- relatorio gerado por agente externo procurando bugs/falhas/melhorias na sessao de automacoes Opus.

## Sinais de saude positivos

- Reserva de emergencia 100% atingida (manter).
- Holerites canonicos 24/24 com paths corrigidos.
- DAS PARCSN 19/19 (proxima reextracao migra para RECEITA_FEDERAL).
- Linking documento->transacao baseline 50% (Sprint 95).
- Smoke aritmetico 8/8 desde Sprint 56.
- Vault Obsidian sync ativo.
- 0 paths quebrados no grafo (Sprint 98a).
- 0 PDFs duplicados em _classificar/ (Sprint INFRA-DEDUP).

## Sinais de quando mudar de rota

- Saude regrediu: pytest perdeu testes, smoke quebrou contrato -> investigar.
- Achado P0 da auditoria externa -> avaliar se vira sprint imediata.
- Re-classificacao introduzir achados que automacoes nao pegam -> abrir nova sub-sprint.

---

*"Saber onde estamos eh metade do caminho." -- principio do snapshot honesto*
