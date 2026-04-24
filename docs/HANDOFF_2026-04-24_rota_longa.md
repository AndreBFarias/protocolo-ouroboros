# HANDOFF — sessão 2026-04-24 (rota longa)

Sessão continuando a rota longa aprovada em `/home/andrefarias/.claude/plans/oi-retomando-o-lazy-zebra.md`.
Atualizado incrementalmente a cada bloco concluído.

---

## Estado inicial (2026-04-24)

- HEAD: `1282b28` (pós-sessão 2026-04-23).
- Baseline: 1261 passed / 9 skipped. Smoke 8/8. Lint OK.
- 10 sprints em backlog prontas para executar em ordem: 87e → F → 93a → 93b → 93c → 92a → 92b → 92c → 82b → D.

---

## Bloco 1 — Cobertura + fidelidade bancária (CONCLUÍDO)

### Sprint 87e — registrar boleto_pdf no pipeline
- Commits: `cec25d0` (incompleto, sem src/pipeline.py) + `59f6423` (fix incluindo o bloco).
- Fecha P1-01. `ExtratorBoletoPDF` agora é descoberto pelo `./run.sh --tudo`.
- +3 testes em `tests/test_pipeline_extratores.py`.

### Sprint F — testes dedicados para 8 extratores bancários
- Commit: `cc78c57`.
- +8 arquivos de teste + 8 fixtures sintéticas (sem dados reais do casal).
- Baseline: 1264 → 1366 passed (+102 testes + 1 xfailed).
- Achado colateral: ExtratorOFX duplica transações (account + accounts). Registrado como **Sprint Fa-ofx-duplicacao** no backlog com teste `xfail(strict=True)` para detectar fix automaticamente.

### Sprint 93a — diagnóstico família A (dedup)
- Commit: `9762040`.
- **Hipótese confirmada empiricamente**: 84-87% dos arquivos em cada diretório bancário são duplicatas SHA-256. O pipeline deduplica; o script de auditoria não. Correção foi no instrumento, não no pipeline.
- Enhancement: flag `--deduplicado` em `scripts/auditar_extratores.py` (SHA físico + dedup nível 1 identificador + nível 2 hash fuzzy).
- Resultados: `itau_cc` e `santander_cartao` → delta R$ 0,00 (OK).
- Relatório: `docs/auditoria_familia_A_2026-04-24.md`.
- +6 testes.

### Sprint 93b — família B (origem histórica + casos mistos)
- Commit: `507c309`.
- Hipótese inicial (origem histórica do `controle_antigo.xlsx`) **rejeitada** — delta persiste restringindo aos meses cobertos. Causa real difere por banco.
- Enhancement: 2 flags novas `--com-ofx` e `--ignorar-ti` (opt-in por banco via gates em `DefinicaoBanco`).
- Resultados:
  - `c6_cartao`: delta R$ 30k → R$ 0,00 (pagamentos de fatura = TI).
  - `nubank_cartao`: delta R$ 64k → R$ 3k (95% reduzido via `--ignorar-ti`).
  - `c6_cc`: diagnosticado (auditor estruturalmente mais fraco que pipeline no OFX). Não corrigido.
  - `nubank_pf_cc`: **dataloss real** de CSVs antigos substituídos por downloads vazios. Sprint 93d endereça.
- Relatório: `docs/auditoria_familia_B_2026-04-24.md`.
- +6 testes.
- Sprint-filhas novas no backlog: **93d** (preservação forte de downloads, P2) e **93e** (coluna `arquivo_origem` no XLSX, P3).

### Sprint 93c — rotulagem Nubank PJ
- Commit: `8c7a83c`.
- **Causa raiz**: `src/extractors/nubank_cartao.py::_parse_linha` emitia `banco_origem="Nubank"` literal fixo, colapsando PJ da Vitória em PF do André. Extrator de CC já estava correto (método `_detectar_conta` preexistente).
- Fix: novo método `_rotular_banco_origem(caminho)` (+17 linhas) espelhando padrão do CC.
- +2 testes.
- Relatório: `docs/auditoria_familia_C_2026-04-24.md`.
- Próximo passo operacional (fora desta sprint): rodar `./run.sh --tudo` para regenerar XLSX com 294 tx PJ-cartão da Vitória agora rotuladas corretamente.

### Resumo Bloco 1

- Baseline: **1261 → 1380 passed / 9 skipped / 1 xfailed** (+119 testes).
- Smoke 8/8 em todos os 6 commits.
- Lint OK em todos.
- `git diff src/extractors/` tocou **apenas nubank_cartao.py** (Sprint 93c) — demais extratores intactos.
- 4 sprints-filhas novas no backlog: **Fa**, **93d**, **93e** (93a/b/c não geraram follow-up além disso).

---

## Achados para o supervisor humano

### 1. Vazamento histórico de PII (pré-sessão)

O commit da Sprint 93c original (pré-2026-04-24) incluiu o CNPJ real do MEI da Vitória (52.488.753) em `docs/sprints/backlog/sprint_93c_rotulagem_nubank_pj.md` linha 72. Na sessão atual, mascarei o CNPJ na spec **antes de movê-la para concluidos**, então o vazamento não se perpetua daqui pra frente.

Porém, **o CNPJ ainda está no histórico git** (1 ocorrência em commit anterior). Isso é um vazamento de PII que só pode ser apagado via history rewrite destrutivo (git filter-repo + force push) — ação que exige autorização explícita e não foi feita.

Também detectei e mascarei na sessão:
- CPF do André + nome completo no relatório `auditoria_familia_B_2026-04-24.md` (linha 48, antes de commitar).
- CPF PF da Vitória em path de CSV no mesmo relatório (linha 140).

Decisão pendente: fazer history rewrite (perigoso em main) ou aceitar. O dado já está publicado no remote (GitHub).

### 2. Commit cec25d0 da Sprint 87e foi incompleto

Por um bug no meu `git add` em paralelo (pathspec inexistente fez o comando inteiro falhar silenciosamente), o `src/pipeline.py` não entrou no commit. O fix foi um commit subsequente `59f6423`. Os dois juntos fecham a Sprint 87e.

### 3. c6_cc permanece com auditor estruturalmente limitado

A Sprint 93b documentou que o auditor (dedup fuzzy simples) não consegue replicar completamente o normalizer + canonicalizer + historico_merger do pipeline real. Para c6_cc, isso significa que mesmo com `--com-ofx` o delta inverte de sinal. Não é bug corrigível sem refazer o auditor. A Sprint D artesanal tratará linha-a-linha qualquer tx suspeita.

### 4. nubank_pf_cc tem dataloss real

Sprint 93d formalizada: preservação forte de downloads em `data/raw/originais/` + reprocessamento cronológico. É trabalho operacional (executar + validar) mais do que código.

---

## Próximos passos

### Bloco 2 — UX cirúrgico (Sprint 92a → 92b → 92c)

Sequencial obrigatório (92a muda páginas que 92b reorganiza que 92c restyle). Inclui:
- 92a: 11 fixes UX (4 P0: labels pyvis humanos, contraste treemap WCAG, completude, rename pagamentos; resto P1+P2).
- 92b: reorganização em 5 clusters (P2-01 das 13 abas estourando viewport).
- 92c: design system CSS vars + Feather icons.

Skill `validacao-visual` será auto-invocada quando diff tocar UI. Stack: Streamlit + Plotly + pyvis, rodando em `http://localhost:8501` via `./run.sh --dashboard`.

### Antes ou durante Bloco 2: regenerar XLSX

Para materializar o fix da Sprint 93c (cartão PJ da Vitória rotulado corretamente), rodar `./run.sh --tudo`. Pode ser feito em qualquer momento — não bloqueia Bloco 2.

### Bloco 3 — Sprint 82b (conta-espelho cartão, ~2h)

### Bloco 4 — Sprint D (auditoria artesanal, interativa com humano)

---

## Invariantes preservados durante a sessão

- Zero emojis em código/docs/commits.
- Acentuação PT-BR correta em tudo.
- Commits limpos sem menção a IA (hook `commit-msg` bloqueia).
- Gauntlet verde commit-a-commit (lint + pytest + smoke 8/8).
- Ressalva → sprint-filha formal. Zero "TODO depois".
- `mappings/pessoas.yaml` e `mappings/senhas.yaml` no .gitignore — não tocados.
- Validação pessoal dos subagentes: `git diff`, gauntlet na main, varredura por dados reais, leitura de relatórios, reprodução dos números.

---

*"Documentar é garantir que o próximo passo exista antes de cair." — princípio anti-crash*
