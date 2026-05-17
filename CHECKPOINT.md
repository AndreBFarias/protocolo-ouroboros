# CHECKPOINT — Estado vivo da sessão

> Atualizado automaticamente pelo Opus principal a cada avanço.
> **Se sessão cair, próximo Opus retoma daqui.** Não editar manualmente.

**Última atualização**: 2026-05-16 ~22:30
**HEAD atual**: `2c46ddf` (pushed em `origin/main`)
**Working tree**: arquivos modificados aguardando commit (README + métricas vivas)

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
  META-CHECK-DADOS-FINANCEIROS-FALSOS-POSITIVOS, META-FIX-FRONTMATTER-YAML-INVALIDO,
  META-FIX-CONCLUIDA-EM-FALTANTES

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

### Sprint-filhas materializadas dos achados (8 no backlog)
- LINK-AUDIT-02-BOOST-DIFF-VALOR-ZERO
- META-FIX-TESTES-E2E-WORKTREE
- INFRA-DEDUP-DAS-PARCSN-DUPLICADO
- ROADMAP-META-LINKING-REDEFINIR
- META-HOOK-SESSION-DINAMICO-RESOLVER-BLACKLIST (BLOQUEADA — aguarda decisão)
- INFRA-TEST-LAST-SYNC-GUARD
- ~~META-NORMALIZAR-TIPO-DOCUMENTO-ETL~~ — **CONCLUÍDA** em `c22aeb5`
- **CATEGORIZER-SUGESTAO-AUDITORIA-RUIDO** (P2, 2h) — TF-IDF tem ruído inaceitável em conf=1.0

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
