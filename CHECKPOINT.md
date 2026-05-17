# CHECKPOINT — Estado vivo da sessão

> Atualizado automaticamente pelo Opus principal a cada avanço.
> **Se sessão cair, próximo Opus retoma daqui.** Não editar manualmente.

**Última atualização**: 2026-05-17 ~02:35
**HEAD atual**: `bc8f578` (pushed)
**Working tree**: limpo
**Auditoria 2026-05-17 em execução**: 8/15 specs concluídas (1 P0 + 3 P1 + 3 P2 + 1 P3)

---

## Contexto resumido

Sessão de auditoria + remediação completa do protocolo-ouroboros. Iniciada em 2026-05-15
com pedido do dono: "auditoria procurando falhas, bugs, oportunidades, DX". Resultou em
21 achados (4 P0 + 8 P1 + 5 P2 + 4 P3). Dono aprovou plano completo de 6 ondas
(α, β, P3-A, P3-B, C, D, E, F) e executei tudo.

**Status**: SESSÃO CONCLUÍDA. Todas as 6 ondas fechadas. Pronto para próximo ciclo de
trabalho ou pausa.

Estado runtime:
- Pytest: **3145 tests collected** (era 3019 no início)
- Smoke: **10/10 contratos OK**
- Lint: **exit 0**
- 9/22 tipos GRADUADOS (gargalo é coleta humana, não código)

Documento mestre da sessão: `docs/auditorias/SESSAO_2026-05-15_AUDITORIA_PROGRESSO.md`
Plano original: `~/.claude/plans/recursive-whistling-goblet.md` (aprovado)

---

## O que foi feito (cumulativo, 54 commits)

### Onda α P0 (estrutural)
- FIX-REGREDINDO-SEMANTICA: separa `_historico_divergencias` vs `_divergencias_ativas`
- META-TIPOS-ALIAS-BIDIRECIONAL: campo `aliases_graduacao` em tipos_documento.yaml
- UX-DASH-GRADUACAO-TIPOS: página Streamlit graduação
- INFRA-PIPELINE-TRANSACIONALIDADE: `GrafoDB.transaction()` context manager
- INFRA-PIPELINE-TX-RESTORE-AUTOMATICO: restore automático em crash

### Onda β P1 paralela (DX)
- META-MAKEFILE-OBSERVABILIDADE: targets `graduados`, `audit`, `spec`, `health-grafo`
- META-SPEC-LINTER: `scripts/check_spec.py`
- META-HOOKS-AUDITAR-E-WIRAR: 15 hooks órfãos movidos para `_arquivado/`

### Onda P3-A (saneamento isolado)
- META-DOC-ROADMAP-PATH, INFRA-RESTORE-CHECKSUM-DIAGNOSTICO,
  META-CHECK-DADOS-FINANCEIROS-FALSOS-POSITIVOS, <!-- noqa: accent -->
  META-FIX-FRONTMATTER-YAML-INVALIDO, META-FIX-CONCLUIDA-EM-FALTANTES <!-- noqa: accent -->

### Onda P3-B
- META-GC-WORKTREES-BRANCHES (`7be8cd9`)
- META-FIXTURES-CACHE-IGNORE
- META-FINISH-SPRINT-GATE-COMPLETO

### Onda P1 (métricas vivas)
- META-ESTADO-ATUAL-AUTO (`2fe1cf3`): `scripts/regenerar_estado_atual.py` + `make estado-atual-atualizar`
- META-ROADMAP-METRICAS-AUTO (`f65e90e`): `scripts/gerar_metricas_prontidao.py` + `make metricas`

### Onda C P1 paralela (2026-05-16)
- INFRA-DEDUP-NIVEL-2-INCLUI-BANCO (`daae4b9`): chave 4-tuple `(data, valor, local, banco_origem)`
- INFRA-TEST-ISOLAR-LAST-SYNC (`283736f`): fixture `cache_isolado` + env var `OUROBOROS_CACHE_DIR`

### Onda D P2 sequencial (dashboard)
- META-PROPOSTAS-DASHBOARD (`b8c1b2b`): 5ª aba "Propostas" cluster Sistema (RECUPERAÇÃO MANUAL de executor órfão)
- AUTO-TIPO-PROPOSTAS-DASHBOARD (`b131027` + `cf7040d` + `d7440c3`): 6ª aba "Tipos por detectar" + `scripts/detectar_tipos_novos.py`
- CATEGORIZER-SUGESTAO-TFIDF (`c45fe35` + `5cd611b` + `bfb3999`): 7ª aba "Sugestor Outros" + `src/transform/categorizer_suggest.py` (TF-IDF manual)

### Onda E P1 supervisor (concorrência)
- INFRA-CONCORRENCIA-PIDFILE (`f4798d1` + `0b884da` + `63909aa` + `c57fdd1`):
  - `src/utils/lockfile.py` (fcntl LOCK_EX|LOCK_NB)
  - integração em `pipeline.executar()` (finally libera mesmo em crash)
  - `flock` em `run.sh` (6 branches mutadores)
  - `_toast_pipeline_ativo()` no dashboard

### Onda F P3 (último, sozinho)
- META-RUFF-FORMAT-NORMALIZAR (`7ffacb5`): 206 arquivos reformatados

### Pós-sessão: meta-auditoria + checkpoint vivo
- CHECKPOINT.md vivo (`7c30229`): doc resiliente entre sessões
- **META-AUDITORIA-CRUZADA-XLSX** (`98fb902`): `scripts/exportar_auditoria_cruzada.py` (380L) + `make auditoria-xlsx`. Gera XLSX com 5 abas. 8 testes verdes. **ACHADO**: ETL grava nomes de tipo_documento divergentes do YAML canônico.
- **META-NORMALIZAR-TIPO-DOCUMENTO-ETL** (`c22aeb5`): script de migração retroativa + 3 extratores atualizados (cupom_termico_foto, nfce_pdf, das_parcsn_pdf). 24 nodes migrados no grafo de produção (das_parcsn_andre→das_parcsn+pessoa, cupom_fiscal→cupom_fiscal_foto, nfce_modelo_65→nfce_consumidor_eletronica). 6 testes do migrador + 3 testes de extrator atualizados. **0 nodes divergentes restantes**.
- **Aba amostras_faltantes + cruzamento por sha8 + promotor (dry-run)** (`2c46ddf`): exportador agora cruza Opus × ETL via sha8 (regex no nome do arquivo). 40 linhas: 5 matches + 19 órfãos ETL + 16 órfãos Opus + 0 divergente. Aba nova `amostras_faltantes` lista 14 tipos PENDENTE/SEM_DOSSIE por prioridade de coleta. `scripts/promover_sugestoes_categoria.py` em dry-run. **ACHADO CRÍTICO**: 319 sugestões com conf≥0.85 têm ruído inaceitável mesmo em conf=1.0 (`Lab Pat e Prev do Cancer → Natação`, `Mp *Barbearia → Bebidas`). Promoção em batch NÃO aplicada. Sprint-filha `CATEGORIZER-SUGESTAO-AUDITORIA-RUIDO` (P2, 2h) materializada.
- **CATEGORIZER-SUGESTAO-AUDITORIA-RUIDO** (`89a03f7`): `mappings/dominio_categorias.yaml` (250L, 22 categorias com tokens_obrigatorios/proibitivos/valor_min_max) + `_avaliar_dominio()` em 4 níveis (BAIXO/MEDIO/ALTO/DESCONHECIDO). 22 sugestões ALTO bloqueadas (incluindo "Tarifa Saque", "Lab Cancer", "Mp Barbearia"). 94 BAIXO seguros, deduplicados em 43 overrides únicos. **Promoção aplicada em `mappings/overrides.yaml`** (17 → 54 entries). Impacto estimado: ~100 transações saem de "Outros" no próximo pipeline. 7 testes regressivos novos.

### Sprint-filhas materializadas dos achados (8 no backlog)
- LINK-AUDIT-02-BOOST-DIFF-VALOR-ZERO
- META-FIX-TESTES-E2E-WORKTREE
- INFRA-DEDUP-DAS-PARCSN-DUPLICADO
- ROADMAP-META-LINKING-REDEFINIR
- META-HOOK-SESSION-DINAMICO-RESOLVER-BLACKLIST (BLOQUEADA — aguarda decisão)
- INFRA-TEST-LAST-SYNC-GUARD
- ~~META-NORMALIZAR-TIPO-DOCUMENTO-ETL~~ — **CONCLUÍDA** em `c22aeb5`
- ~~CATEGORIZER-SUGESTAO-AUDITORIA-RUIDO~~ — **CONCLUÍDA** em `89a03f7` (43 overrides promovidos)

### Auditoria independente 2026-05-17 (15 specs novas)

3 Explore agents em paralelo + validação manual revelou **1 bug P0 crítico** + 14 oportunidades:

**Categoria A — Código/Pipeline:**
- **`AUDIT-CATEGORIA-REGRA-VALOR-SINAL` (P0!)** — `_verificar_regra_valor` usa `valor < 800` com sinal: TODA despesa KI-SABOR vira Padaria, nunca Aluguel. Bug afeta TODAS regras com `regra_valor` (>=, <, etc).
- `INFRA-DESCOBRIR-EXTRATORES-REFATORA` (P2) — 166L com 23 try/except idênticos → 30L via pkgutil + env var
- `INFRA-PIPELINE-FASES-ISOLADAS` (P2) — `_executar_corpo_pipeline` 156L → 16 fases isoladas com stats
- `INFRA-SCRIPTS-CLI-PADRAO` (P3) — 15+ scripts com `sys.path.insert` hardcoded + 10 sem --help
- `AUDIT-TI-RECLASSIFICA-RASTREAMENTO` (P1) — `_reclassificar_ti_orfas` muta silenciosamente sem log granular
- `INFRA-PDF-TIMEOUT` (P2) — pdfplumber sem timeout pode hangar pipeline

**Categoria B — Dashboard/UX/Testes:**
- `UX-CACHE-BUSCA-TTL-CURTO` (P2) — busca.py ttl=300s causa dados obsoletos 5min
- `UX-SPINNER-PROGRESS-FEEDBACK` (P3) — só 2/42 páginas com `st.spinner` em operações lentas
- `UX-BE-SESSION-STATE-SAFE` (P2) — `pop()` sem default crash em deep-link primeira visita
- `TEST-EXTRAIR-HELPERS-PUROS` (P3) — 10+ testes importam Streamlit desnecessariamente

**Categoria C — Dados/Limpeza:**
- `SEC-SENHAS-PARA-ENV` (P1) — migrar `mappings/senhas.yaml` para `.env` + python-dotenv
- `INTAKE-FALLBACK-CPFS-AUSENTE` (P1) — `pessoa_detector` falha silenciosa se YAML ausente
- `GRAFO-AUDIT-ORPHAN-NODES` (P3) — 3 nodes fornecedor sem edges (1 BIR COMERCIO, 1 DIRPF, 1 CNPJ MEI)
- `CLEANUP-DATA-OUTPUT-DIRETORIOS` (P3) — 3 diretórios obsoletos em `data/output/` acumulando
- `META-REGEN-INDICE-BACKLOG` (P3) — INDICE_2026-05-12 declara 113 specs, real são 145 hoje

**2 achados eram FALSO POSITIVO** (validados manualmente):
- `pagamentos_valores.py` órfão → NEGADO (importado em `pagamentos.py:52`)
- `dominio_categorias.yaml` não consumido → NEGADO (consumido em `categorizer_suggest.py` 10x)

### Execução em curso (uma por vez, foreground)

| # | Sprint | Commit | Status |
|---|---|---|---|
| 1 | AUDIT-CATEGORIA-REGRA-VALOR-SINAL (P0) | `7328cd6` | CONCLUÍDA. `abs(valor)` em `_verificar_regra_valor`. 4 testes regressivos. Bug confirmado mas sem impacto produção (normalizer já abs antes). |
| 2 | SEC-SENHAS-PARA-ENV (P1) | `85c0239` | CONCLUÍDA. `src/utils/segredos.py` + `.env.example` + refatora `senhas.py` (YAML fallback). 9 testes regressivos. |
| 3 | INTAKE-FALLBACK-CPFS-AUSENTE (P1) | `c442e70` | CONCLUÍDA. Log WARNING se `.example` existe + smoke check em `--check` (24 checagens). 2 testes regressivos. |
| 4 | AUDIT-TI-RECLASSIFICA-RASTREAMENTO (P1) | `62850cd` | CONCLUÍDA. Flag `_reclassificada_68b` + log estruturado `reclassificacao_ti_orfas_<ts>.json`. 3 testes regressivos. |
| 5 | INFRA-DESCOBRIR-EXTRATORES-REFATORA (P2) | `c819adc` | CONCLUÍDA. `EXTRATORES_CANONICOS` lista declarativa + env var. 166L → 52L (-114L). 5 testes regressivos. |
| 6 | INFRA-PDF-TIMEOUT (P2) | `ad78d32` | CONCLUÍDA. `_pdf_timeout.py` via SIGALRM + aplicado em danfe + garantia. 7 testes regressivos. |
| 7 | UX-CACHE-BUSCA-TTL-CURTO (P2) | `5cf9685` | CONCLUÍDA. ttl 300s→60s + invalidação por mtime do XLSX. 2 testes regressivos. |
| 8 | CLEANUP-DATA-OUTPUT-DIRETORIOS (P3) | `b0c1465`+`bc8f578` | CONCLUÍDA. Script + execução real: 3 diretórios obsoletos limpos (~670 KB), 2 movidos para `_arquivo_historico/2026-05-17/`. |

**Restantes** (em ordem):
- UX-BE-SESSION-STATE-SAFE (P2, 1h) — `pop()` sem default crash em deep-link
- INFRA-PIPELINE-FASES-ISOLADAS (P2, 3h) — `_executar_corpo_pipeline` 156L
- INFRA-SCRIPTS-CLI-PADRAO (P3, 2h) — padrão CLI canônico
- UX-SPINNER-PROGRESS-FEEDBACK (P3, 1.5h) — 2/42 páginas com spinner
- TEST-EXTRAIR-HELPERS-PUROS (P3, 2h) — testes importam Streamlit
- GRAFO-AUDIT-ORPHAN-NODES (P3, 1h) — 3 nodes fornecedor sem edges
- META-REGEN-INDICE-BACKLOG (P3, 0.5h) — INDICE_2026-05-12 desatualizado

---

## Próximos passos exatos (caso retome trabalho)

### Opção 1 — Aceitar a sessão como concluída
Não há trabalho pendente do mandato original. Pausar até dono levantar nova demanda.

### Opção 2 — Atacar sprint-filhas acumuladas (ordem de prioridade)
1. **META-HOOK-SESSION-DINAMICO-RESOLVER-BLACKLIST** (P2, 0.5h) — *bloqueada*, requer decisão do dono (3 rotas A/B/C na spec).
2. **LINK-AUDIT-02-BOOST-DIFF-VALOR-ZERO** (P2, 2h) — boost diff_valor=0 em `_calcular_score`. Resolve 14 empates restantes do LINK-AUDIT-01. Não-bloqueada.
3. **INFRA-DEDUP-DAS-PARCSN-DUPLICADO** (P2, 1h) — doc 7664 e 7671 mesma realidade. Não-bloqueada.
4. **ROADMAP-META-LINKING-REDEFINIR** (P2, 0.5h) — meta 30% inalcançável. Trocar denominador.
5. **INFRA-TEST-LAST-SYNC-GUARD** (P3, 0.5h) — hook pre-commit bloqueia path `/tmp/`.
6. **META-FIX-TESTES-E2E-WORKTREE** (P3, 1.5h) — 23 testes playwright pulam quando data/ ausente.

### Opção 3 — Onda nova (escolha do dono)
- Validação humana via Revisor (sessão dedicada com Opus de apoio)
- Coleta de amostras para os 13 tipos PENDENTE (gargalo humano, ETL pronto)
- Início do Épico 4 (IRPF) ou Épico 5 (UX dashboard refinement)

---

## Decisões pendentes do dono

### CRÍTICA (bloqueia retomada de META-HOOK-SESSION-DINAMICO)
Spec `META-HOOK-SESSION-DINAMICO-RESOLVER-BLACKLIST` lista 3 rotas:
- **A** — Remover exceções do `.gitignore` (alinhar com blacklist global). Hook fica local-only.
- **B** — Adicionar exceção na blacklist global `~/.config/git/anonymity-blacklist.txt`.
- **C** — Mover script de `.claude/hooks/` para `hooks/`.

### NORMAL (não bloqueia, mas precisa input)
- **ROADMAP-META-LINKING-REDEFINIR**: trocar meta de "30% das transações" para "80% dos documentos"? (Mais honesto, mas redefine compromisso original.)
- **AUTO-TIPO + CATEGORIZER**: ambos têm botões que escrevem em arquivos canônicos (`tipos_documento.yaml`, `overrides.yaml`). Dono confirma que workflow é: dashboard mostra → dono clica "aceitar" → entry adicionada → dono refina manualmente?

---

## Arquivos modificados ainda não commitados

**Nenhum.** Working tree limpo. Todos os 54 commits da sessão estão em `origin/main`.

---

## Como retomar se sessão cair

```bash
cd /home/andrefarias/Desenvolvimento/protocolo-ouroboros
git log --oneline -5            # confirma HEAD em 9750293
git status                       # esperado: clean
cat CHECKPOINT.md                # ler este arquivo
cat docs/auditorias/SESSAO_2026-05-15_AUDITORIA_PROGRESSO.md  # mapa completo

# Atualizar baseline runtime:
make metricas
make estado-atual-atualizar
make smoke

# Se quiser retomar sprint-filhas:
ls docs/sprints/backlog/ | grep -E "LINK-AUDIT-02|INFRA-DEDUP-DAS|INFRA-TEST-LAST-SYNC-GUARD"
```

Documento de continuidade canônico: `docs/auditorias/SESSAO_2026-05-15_AUDITORIA_PROGRESSO.md`
Plano original aprovado: `~/.claude/plans/recursive-whistling-goblet.md`

---

## Checkpoint protocol (regra para todo Opus que continuar)

A cada commit pushed que muda estado material do sistema:
1. Atualizar HEAD + tabela "O que foi feito" + working tree no CHECKPOINT.md.
2. Apendar entry na tabela apropriada de `docs/auditorias/SESSAO_2026-05-15_AUDITORIA_PROGRESSO.md`.
3. Rodar `make metricas && make estado-atual-atualizar` se runtime mudou.
4. Commitar CHECKPOINT.md + docs vivas em commit dedicado `docs(checkpoint): <evento>`.

Frequência: **sempre que avançar algo material.** Não acumular > 1 sprint sem atualizar.
