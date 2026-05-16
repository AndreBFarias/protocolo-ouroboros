# ESTADO_ATUAL.md -- Snapshot técnico em 2026-05-12 (Fase A inteira + 8 sprints executadas + bug C6 massivo resolvido)

> **Versionado a partir de 2026-04-29 pela Sprint DOC-VERDADE-01.A. Última atualização em 2026-05-12 (parte 6): Fase A completa (4 validações artesanais multimodais + 8 sprints executadas via executors paralelos + descoberta arquitetural de 253 duplicações OFX+XLSX no C6 / ~43% do banco)**.
> Whitelist em `.gitignore` permite este arquivo + COMO_AGIR.md no repo (POR_QUE.md e PROMPT_NOVA_SESSAO.md continuam locais por conter PII estrutural).
> Esta doc é fotografia do momento — para verdade viva consulte `git log` + `ls docs/sprints/concluidos/`.
> Para auditar este snapshot contra realidade: `python scripts/auditar_estado.py`.

## Sessão 2026-05-12 (parte 6) -- Fase A completa + bug C6 arquitetural resolvido

**Estado runtime (2026-05-12 23:10)**: HEAD `79f54c5`. Pytest **2830 collected** (+78 vs início da sessão). Smoke 10/10. Lint exit 0. 22 commits pushed na sessão.

### 8 sprints executadas via executors paralelos (todos pushed)

| # | Sprint | Executor SHA | Merge SHA |
|---|---|---|---|
| 1 | INFRA-OPUS-SCHEMA-EXTENDIDO | `59b0170` | direto main |
| 2 | MOB-bridge-4-inbox-subtipos-reader | `e6390eb` | `e9f13ea` |
| 3 | INFRA-NFCE-FIX-PS5-P55 | `cb9e216` | `3d659bb` |
| 4 | INFRA-DAS-EXTRAIR-COMPOSICAO | `cd96a42` | `eec9c2e` |
| 5 | INFRA-CONTRACHEQUE-EXTRAIR-BASES | `257942d` | `8a7dfda` |
| 6 | INFRA-CATEGORIZAR-SALARIO-G4F-C6 | `4f82e26` | `b0e76cd` |
| 7 | INFRA-DEDUP-LANCAMENTO-DUPLICADO-G4F | `5b271ef` | `a81ac7d` |
| 8 | INFRA-DEDUP-C6-OFX-XLSX-AMPLO | `2998b26` | `d6758f6` |

### Achado massivo descoberto e resolvido

A sprint #7 (DEDUP-LANCAMENTO-DUPLICADO-G4F) investigou um par duplicado isolado e revelou padrão **arquitetural**: 253 pares duplicados no C6 (~510 linhas, ~43% do C6/pessoa_a) por **ingestão dupla OFX+XLSX**. Causa-raiz: `src/transform/deduplicator.py::deduplicar_por_hash_fuzzy` usa chave `(data, valor, local)` e o campo `local` derivado da descrição é estruturalmente diferente entre OFX (prefixo "RECEBIMENTO SALARIO -") e XLSX (sem prefixo).

Sprint #8 (DEDUP-C6-OFX-XLSX-AMPLO P0) implementou **Opção 2 ampliada** (commit `2998b26`):
- `_normalizar_local_para_chave` remove prefixos OFX antes do dedup
- `_riqueza_descricao` preserva OFX vs XLSX (OFX é mais informativo no C6)
- `_consolidar_pares_ofx_xlsx_mesmo_banco` pass 2b por `_arquivo_origem`

Cross-check Itaú/Santander/Nubank: padrão **não** se repete (Itaú/Santander sem OFX, Nubank com estrutura compatível). Detalhe em `docs/auditorias/DEDUP_AMPLO_INVESTIGACAO_2026-05-12.md`.

**Limitação conhecida**: XLSX consolidado (`data/output/ouroboros_2026.xlsx`) **não foi regenerado pelo agente** para não conflitar com worktrees paralelos. Dono deve rodar `make run` no main para regenerar e confirmar 253 pares desaparecem.

### Validações artesanais multimodais (Fase A do supervisor)

4 tipos × 2 amostras = 8 amostras lidas via Read multimodal Opus 4.7:

| Tipo | Amostras | Veredito | Relatório |
|---|---|---|---|
| CUPOM | 4 NSP + 1 Vitória | REPROVADO inicial → 5 caches promovidos | `VALIDACAO_ARTESANAL_CUPOM_2026-05-12.md` |
| HOLERITE | G4F + Infobase fev/2026 | APROVADO_COM_RESSALVAS | `VALIDACAO_ARTESANAL_HOLERITE_2026-05-12.md` |
| DAS PARCSN | parcela 4/25 + 17/25 | APROVADO_COM_RESSALVAS | `VALIDACAO_ARTESANAL_DAS_2026-05-12.md` |
| NFCe | PS5 + supermercado | APROVADO_COM_RESSALVAS_CRITICAS | `VALIDACAO_ARTESANAL_NFCE_2026-05-12.md` |

### Em execução agora (2 executors background)

- **INFRA-NFCE-DEDUP-OCR-DUPLICATAS** (agentId `a74f5fd0fcf3f9841`, P1, ~3h) — dedup tolerante a OCR no grafo NFCe (4 nodes → 2 esperado).
- **DASH-PAGAMENTOS-CRUZADOS-CASAL** (agentId `a9fde3b382b451e97`, P2, ~2h) — pessoa_pagadora vs pessoa_devedora + bloco dashboard + pacote IRPF.

### Sprint-filhas pendentes em backlog (P1+ não-executadas)

- INFRA-SUBSTITUIR-CACHE-SINTETICO-CUPOM (P0, 5 caches já promovidos local pelo supervisor; resta validar via gauntlet)
- INFRA-IMPORTAR-SANTANDER-ANDRE (P2, gerada por CATEGORIZAR-G4F-C6 como spec-filha)
- INFRA-LINT-ACENTUACAO-SPECS-2026-05-12 (P3, saneamento)

### Sprints originais ainda em backlog (Onda 6/7)

Não executadas nesta sessão:
- `MOB-bridge-5-classifier-pix` (depende DOC-27)
- `MOB-dashboard-mostra-pix-app`
- `MOB-audit-estrutura-vault-md`
- `MOB-spec-exercicios-gif-timer`
- `MOB-spec-transcricao-audio`
- `MOB-spec-galeria-memorias`
- `MOB-bug-camera-momento-repro`
- `UX-AUDIT-VISUAL-2026-05-12`

### Padrões canônicos descobertos e formalizados nesta sessão

Adicionados em `VALIDATOR_BRIEF.md` (letras `(w)`-`(aa)` já estavam ocupadas com outras semânticas; descobertos viraram `(dd)`-`(hh)`):

- **(dd)** Stash chain hazard: agente background com worktree compartilhado pode dropar trabalho do supervisor via `git stash` mal-encadeado.
- **(ee)** Schema-extension precede validation: nunca crie test/fixtures que dependam de schema antes do schema existir.
- **(ff)** Auditoria automática vs supervisor: lê texto da spec, supervisor lê texto contra grep. Padrão `(s)` Validação ANTES só funciona se executado.
- **(gg)** Cache sintético é placeholder honesto que vira mentira silenciosa quando consumido como gabarito.
- **(hh)** Ingestão dupla OFX+XLSX escapa dedup quando `local` é estruturalmente diferente entre as fontes.

### Regra revogada

**(h) Limite 800 linhas por arquivo**: REVOGADA pelo dono em 2026-05-12. Splits ficam por critério de legibilidade humana, não regra fixa. As 6 specs `INFRA-SPLIT-*` em backlog mantidas mas perderam prioridade automática.

### Caches Opus promovidos a gabaritos reais (local, em `data/output/opus_ocr_cache/`)

5 caches do tipo `cupom_fiscal_foto`:
- `2e43640d` (propagado de 6554d704)
- `6554d704` (NSP 27/04 — 49 itens alta confiança)
- `67a3104a` (NSP 24/04 — 22 itens alta confiança)
- `bc3c42aa` (propagado de 67a3104a)
- `37a8a111` (Vitória farmácia 23/04 — 2 itens alta confiança)

Backup dos 4 sintéticos em `data/output/opus_ocr_cache_sintetico_backup/`. 6 fixtures pytest lixo movidas para `data/output/opus_ocr_pendentes_lixo_2026-05-12/`.

---

## Sessao 2026-05-12 (parte 2) -- Retomada apos travamento: auditoria + 8 patches + schema 11 tipos

**Pretexto**: sessao anterior travou apos produzir 15 specs + 3 auditorias + INDICE sem commit. Retomada para organizar, ajustar e disparar a Onda 6.

### Auditoria profunda das 14 specs (supervisor manual contra codigo)

Revisor automatizado via Explore deu 9 PRONTAS / 5 REVISAR / 0 REPROVAR. Supervisor (eu) refez auditoria 1-a-1 contra `grep` em `src/`. Resultado real: **7 PRONTAS / 6 REVISAR / 1 REPROVAR**.

| Spec | Veredito real | Problema concreto |
|---|---|---|
| INFRA-VALIDACAO-CUPOM | REVISAR | modulo `cupom_foto` inexistente -> canonico `cupom_termico_foto.py::ExtratorCupomTermicoFoto::extrair_cupom` |
| INFRA-VALIDACAO-DAS | REVISAR | placeholder "verificar nome" -> `ExtratorDASPARCSNPDF::extrair_das` retorna dict |
| MOB-audit-vault | REVISAR | `boleto` listado em financeiro mas categorias.ts nao tem; spec usava `binario_companion` mas campo real eh `arquivo` |
| **MOB-bridge-4** | **REPROVAR** | mira `inbox_reader.py` que eh PURO LEITOR. Alvo real: `inbox_processor.processar_inbox` (linha 173 `iterdir()` plano) + `intake/orchestrator` + `intake/registry` |
| MOB-bridge-5 | REVISAR | sobrepoe escopo de DOC-27. Cortado para apenas conectar |
| MOB-dashboard-pix | REVISAR | sidecar real `inbox/.extracted/`, nao `vault_path/.extracted/` |
| UX-AUDIT-VISUAL | REVISAR | sem metodo objetivo de medicao |

### 8 patches aplicados nesta sessao

1. CUPOM: extrator canonico
2. DAS: assinatura real
3. MOB-audit-vault: alinhamento com categorias.ts + frontmatter `tipo: inbox_arquivo`
4. MOB-bridge-4: reescrita parcial -- alvo correto + 4 Edits explicitos
5. MOB-bridge-5: escopo cortado, bloqueado por DOC-27
6. MOB-dashboard-pix: path sidecar real + `OUROBOROS_VAULT_PATH`
7. UX-AUDIT-VISUAL: formula 0.5SSIM + 0.3hist + 0.2estrutural
8. ADRs renumeradas para 26-29 sequenciais

### Commit `59b0170` -- schema OCR estendido (executor background)

Schema `mappings/schema_opus_ocr.json` agora cobre **11 valores em `tipo_documento`** (5 antigos + 6 novos: holerite, das_parcsn, nfce_modelo_65, boleto_pdf, danfe_55, extrato_bancario_pdf) com blocos `allOf if/then` por tipo. Retrocompat hard: 4 caches existentes em `data/output/opus_ocr_cache/` permanecem validos.

Entregas do commit `59b0170`:
- `mappings/schema_opus_ocr.json` (313 linhas)
- `tests/test_opus_ocr_schema.py` (249 linhas, **21 testes**)
- `tests/fixtures/opus_ocr_schemas/` (6 fixtures)
- Pytest: **2758 passed / 14 skipped / 1 xfailed** (era 2726 -> +32 net)
- Smoke: **10/10 contratos OK**
- Spec `sprint_INFRA_opus_schema_extendido.md` movido para `concluidos/`

### Armadilha do executor-sprint: stash mal-encadeado

Licao: executor-sprint rodando em background com `isolation: "worktree"` editou paths absolutos para o main worktree em vez do worktree proprio. Fez `git stash -u` para pytest baseline limpo. Em algum momento o stash sumiu, supervisor (eu) teve de fazer `git stash pop` que aplicou parcialmente. Recuperado pelo commit `59b0170` que sobreviveu.

Novos padroes canonicos:
- **(w)** Stash chain hazard: agente background com worktree compartilhado pode dropar trabalho do supervisor.
- **(x)** Schema-extension precede validation: nunca crie test/fixtures que dependam de schema antes do schema estar gravado.
- **(y)** Auditoria automatica le texto; supervisor le texto contra grep. Discrepancia de ~30% prova que validacao ANTES (padrao `(k)`) so funciona se executada.

### Proximas etapas (Onda 6, 14 specs PRONTAS)

1. Validacao artesanal CUPOM_2e43640d.jpeg (supervisor multimodal + comparar com ETL via `ExtratorCupomTermicoFoto`).
2. MOB-bridge-4 (executor apos validacao CUPOM).
3. Validacao artesanal HOLERITE (1 G4F + 1 Infobase).
4. Validacao artesanal NFCE (foco P55/PS5).
5. Validacao artesanal DAS (1 pre-107 + 1 pos-107).

---

## Sessao 2026-05-06 (parte 4) -- Onda M COMPLETA (4 sub-sprints + zero débito residual)

**Onda M FECHADA em 2026-05-06**, validada visualmente side-by-side (mockup vs dashboard real via `claude-in-chrome`) pelo supervisor (padrão `(p)`). Branch `ux/onda-m` pronta para merge em `main`.

### 4 sub-sprints paralelas executadas via subagents `executor-sprint` (worktrees isolados)

| Sprint | Commit | Cluster | Métrica |
|---|---|---|---|
| UX-M-02.A | `e1ccd55` | Documentos (7 páginas) | imports tema→ui em 7/7 |
| UX-M-02.B | `c564b92` | Finanças (4 páginas) | imports tema→ui em 4/4 |
| UX-M-02.C | `6d36249` | Análise+Metas+Inbox+Sistema (6 páginas) | imports parciais (3/6); 3 overrides justificados |
| UX-M-02.D | `b413ac7` | Bem-estar (17 páginas, 4 com CSS local) | 4 páginas-chave migradas; 4 overrides justificados |

### 2 fixes residuais (zero-débito) executados pelo supervisor

| Fix | Commit | Métrica |
|---|---|---|
| `css/paginas/` + helper `carregar_css_pagina` + bug "undefined" Plotly | `9309ff8` | -971L em 6 páginas + 6 CSS criados |
| Overrides Bem-estar para `css/paginas/be_*.css` | `2a28aee` | -381L em 4 páginas + 4 CSS criados |

### Métricas finais Onda M completa

- 30 páginas migradas para `ui.py` + classes canônicas.
- 10 arquivos CSS dedicados em `src/dashboard/css/paginas/` (busca, catalogacao, extrato, categorias, inbox, skills_d7, be_hoje, be_humor, be_diario, be_eventos).
- Helper `carregar_css_pagina(nome)` em `ui.py` segue padrão `tema_css.py:65`.
- `tema_plotly.py`: bug do `title.font` sem `title.text` corrigido (gerava placeholder "undefined" em todos os Plotly charts).
- **Redução total Python**: -1352L em paginas/.
- **Pytest baseline**: 2555 passed / 14 skipped / 1 xfailed = 2570 (mantida; 22 fails preexistentes flaky resolvidos no caminho).
- **Validação visual side-by-side**: 9 páginas confrontadas mockup vs dashboard real (Projeções, Busca, Extrato, Categorias, Inbox, Skills D7, Be-hoje, Be-humor, Be-diário). Zero regressão.

---

## Sessao 2026-05-06 (parte 3) -- Onda M FASE CENTRAL CONCLUÍDA (modularização do dashboard)

**5 sprints da Onda M concluídas em 2026-05-06**, todas validadas pessoalmente pelo supervisor (padrão (p)) — branch `ux/onda-m`, ainda não merged em main:

| # | Sprint | Commit | Esforço | Métrica chave |
|---|---|---|---|---|
| 1 | UX-M-01 (tokens) | `bbedf2c` | 30min | tokens.css 137L canônico; tema_css.py -95L |
| 2 | UX-M-04 (shell) | `2947f2b` | 16min | shell.py 211→72L; setProperty 56→2 |
| 3 | UX-M-TESTES (4 testes) | `da8f639` | 30min | 4 testes pré-existentes corrigidos |
| 4 | UX-M-02 (ui.py) | `3ef1d66` | 25min | ui.py 684L com 14 funções; tema.py 723→454L |
| 5 | UX-M-03 (components.css) | `2544160` | 25min | tema_css.py 1619→987L (-632); 3 CSS canônicos |

**Métricas Onda M consolidadas:**
- `tema_css.py`: 1675 → 987 linhas (-688, -41%)
- `tema.py`: 723 → 454 linhas (-269, -37%)
- `shell.py`: 604 → 465 linhas (-139, -23%)
- `setProperty` JS runtime: 56 → 2 (96% migrado para CSS estático)
- 5 arquivos CSS canônicos criados em `src/dashboard/css/`: tokens.css, components.css, shell.css, overrides_streamlit.css, extensoes_dashboard.css
- `ui.py` criado como fronteira pública única com 14 funções (9 migradas + 3 novas + 2 re-exports)

**Pytest baseline:** 2555 passed / 14 skipped / 1 xfailed (era 2018 do ESTADO_ATUAL.md original — desatualizado pré-Onda T+Q+U).

**Validação visual (5 páginas amostradas em cada sprint):** zero regressão visual — sidebar 240px, topbar full-width, page-headers UPPERCASE, KPIs com bordas semânticas, layouts internos preservados.

**Próximo passo (4 sub-sprints UX-M-02.A..D — migração de páginas):**
Cluster Documentos (A), Finanças (B), Análise+Metas+Inbox+Sistema (C), Bem-estar (D) — paralelos, ~16h total. Devem rodar em **nova sessão Claude Code com prompt canônico** (contexto fresco), pois Opus principal atual já está pesado.

Após sub-sprints verdes: merge `ux/onda-m` → `main` finaliza Onda M.

---

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

<!-- BEGIN_AUTO_METRICAS -->
```
TESTES: 3108 tests collected in 2.70s
SMOKE: 10/10 contratos OK
LINT: exit 0
GRAFO: 7639 nodes / 25027 edges
TIPOS GRADUADOS: 9/23 no mappings/tipos_documento.yaml
EXTRATORES: 23 em src/extractors/
ÚLTIMO COMMIT: b8c1b2b feat(META-PROPOSTAS-DASHBOARD): pagina dashboard de propostas pendentes
```
<!-- END_AUTO_METRICAS -->


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
