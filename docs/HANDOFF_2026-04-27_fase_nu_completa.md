# HANDOFF -- 2026-04-27 (Fase NU completa + P1 98+101 + Sprint 98-1 + --executar 98)

> Sessão maratona iniciada em 2026-04-26 (segunda parte) e fechada em 2026-04-27 (primeiras horas). Continuidade direta do HANDOFF_2026-04-24 + AUDITORIA_2026-04-26.

## Resumo de uma frase

Fase NU **fechou** com 6 sprints P0 entregues (95, 96, D2, 97, 90a, 90b) + Sprint 98-1 diagnóstica + `--executar` da 98 aplicado em runtime real (limpeza histórica de 97 fósseis bit-a-bit) + Sprints P1 98 e 101 concluídas. pytest 1.530 → 1.620 (+90). 16 commits em main, todos pushed em commit `7cc4c68` (+ 8 commits adicionais não-pushed ainda neste arquivo de handoff -- ver seção "Estado git").

## Tabela executiva da rodada

| # | Sprint | Commit | Entregas-chave | Testes |
|---|--------|--------|----------------|-------|
| 0 | (continuação auditoria) | `ff38a4b` | Edit-pronto + closure auditoria 2026-04-26 + 12 specs novas | -- |
| 1 | 95 (P0 linking runtime) | `2df40ae` | `peso_temporal_diario` configurável por tipo + janela ampla por tipo + 5 testes; **0 → 23 arestas `documento_de`** (56% docs vinculados) | +5 |
| 2 | 96 (P0 classifier OCR-curto) | `9befcb5` | schema `regras: [{tipo, requer_todos, requer_qualquer, ocr_minimo, ocr_maximo}]` retrocompatível + 9 testes; **`inbox/1.jpeg` deixa de classificar `None`** | +9 |
| 3 | D2 (P0 revisor visual) | `b3026a7` | `revisor.py` 616L + `listar_pendencias_revisao` + 24 testes + 3 screenshots WCAG-AA + SQLite + PII mascarada em 4 sítios | +24 |
| 4 | 97 (P0 page-split heterogêneo) | `22c9e5e` | predicado puro `e_heterogeneo_por_classificacao` + branch reversível + 14 testes; zero regressão para extratos homogêneos | +14 |
| 5 | 90a (P0 inbox detecta holerite) | `b8ab3fe` | hipótese da spec rejeitada empiricamente; defesa em 2 camadas (YAML especifico + `_ASSINATURAS_HOLERITE` no registry) + 8 testes | +8 |
| 6 | 90b (P0 DAS PARCSN drift) | `c136ea6` | hipótese OCR rejeitada; causa real era regex sem `ç` + período "Diversos"; classe `[A-Za-zÀ-ÿ]+` + `_RE_PERIODO_DIVERSOS` + `_RE_PAGAR_ATE` priorizado em literal + 8 testes; **10 → 19 nodes DAS PARCSN** | +8 |
| 7 | 101 (P1 --full-cycle) | `d615488` | branch `--full-cycle` em `run.sh` (encadeia inbox+tudo, aborta se inbox falhar) + opção R no menu + 8 testes | +8 |
| 8 | 98 (P1 script migração) | `835f0a7` | `scripts/migrar_holerites_retroativo.py` 427L com `--dry-run` (default) + `--executar`; idempotência SHA-256; preserva originais (ADR-18) | -- |
| 9 | 98-1 (P2 diagnóstico engine) | `84b071e` | 3 hipóteses REJEITADAS empiricamente; engine atual íntegra; causa raiz dos 91 fósseis = pré-Sprint 90a + pré-Sprint 41 P2.3; 5 testes regressivos novos | +5 |
| 10 | 98 `--executar` | `a48b843` | **121/121 ações aplicadas, zero falhas; -97 PDFs físicos; +24 holerites canônicos** | (runtime) |

## 4 sub-sprints abertas como achados colaterais (anti-débito, todas formalizadas)

| Sprint | Prio | Estimativa | Tema | Origem |
|--------|------|------------|------|--------|
| 95a | P2 | ~1h | Holerite persistir `liquido` separado de `total` no metadata | Sprint 95 (linker tolera 0.30 mas líquido permitiria 0.05) |
| 95b | P3 | ~2h | Linker aceitar âncora temporal alternativa (`vencimento` para DAS) | Sprint 95 (reduziria 14+7=21 propostas de conflito) |
| 95c | P3 | ~30min | Corrigir 8 sítios `# noqa: accent` inválidos | Sprint 95 (warning ruff, não bloqueia) |
| INFRA-D2a | P3 | ~30min | Extrair `listar_pendencias_revisao` para `dados_revisor.py` | Sprint D2 (`dados.py` cresceu 836L → 976L) |
| 90a-1 | P3 | ~1h | Endurecer `file_detector._detectar_pdf` na causa raiz | Sprint 90a (fix em 2 camadas, esta seria a 3a definitiva) |

Sprint **98-1** já fechada (diagnóstico mostrou que engine está íntegra).

## P1 ainda pendentes (sessão futura)

- **Sprint 99** (P1, ~1h) -- redactor PII em logs INFO. Spec OK em `docs/sprints/backlog/`.
- **Sprint 100** (P1, ~2h) -- deep-link tab funcional dentro de cluster. Spec OK.

## P2/P3 backlog histórico (sem urgência)

- Sprint 102 (pagador vs beneficiário IRPF cross-casal).
- Sprint 93h (limpeza simétrica clones André).
- Sprint Fa (OFX duplicação account+accounts).
- Sprint 93d (preservação forte downloads + reprocessamento cronológico).
- Sprint 93e (propagar `_arquivo_origem` como coluna XLSX).

## Achado novo da sessão NU (sprint a criar nesta rodada)

- **Teste flaky `test_processar_duas_vezes_nao_duplica_artefatos`** em `test_pdf_heterogeneo_multitype.py`: passa isolado mas falha aleatoriamente em suite full. Provável race condition ou state compartilhado em fixture. Spec a criar: `sprint_INFRA_97a_test_flaky_idempotencia.md` (P3, ~1h).

## Métricas pós-NU

| Métrica | Início (commit `1fa50bc`) | Fim (commit `a48b843`) | Δ |
|---|---|---|---|
| pytest passed | 1.530 | **1.620** | +90 |
| Documentos no grafo | 41 | 50 | +9 (DAS PARCSN destravados) |
| Arestas `documento_de` | 0 | 25 | +25 (linking runtime ativo) |
| % docs vinculados | 0% | **50%** | +50pp |
| DAS PARCSN nodes | 10 | 19 | +9 (drift -47% → 0%) |
| Aba Revisor | inexistente | live | -- |
| `inbox/1.jpeg` classifica | `None` | `cupom_fiscal_foto/ocr_curto` | -- |
| PDFs heterogêneos `_classificar/` | acumulam | fatiam + reverte se homogêneo | -- |
| Holerite cai em pasta bancária | sim | bloqueado (defesa em 2 camadas) | -- |
| Fósseis G4F em itau_cc + santander_cartao | 91 | 0 | -97 PDFs físicos limpos |
| Holerites com nome canônico | 0/30 | **24/24** | regularizados |

## Padrões canônicos descobertos nesta sessão (formalizados em VALIDATOR_BRIEF rodapé)

(j) **Disciplina de worktree:** prefixar `cd "$WORKTREE_PATH" && ...` em todo Bash do executor; verificar `pwd; git rev-parse --show-toplevel; git branch --show-current` antes de cada commit. 3 sprints (95, 97, 90b) caíram em main por engano de cwd; 90b detectou e reverteu antes de commitar.

(k) **Hipótese da spec não é dogma:** Sprints 90a, 90b e 98-1 descobriram empiricamente que a hipótese principal estava errada. Subagent rodou diagnóstico SQL/python/grep antes de codar e mudou abordagem.

(l) **Subregra composta retrocompatível:** Sprint 96 estendeu schema do classifier YAML adicionando lista de subregras sem quebrar 20 outros tipos.

(m) **Branch reversível:** Sprint 97 fez page-split tentativo + verificação semântica + descarte ou commit. Garante zero regressão.

(n) **Defesa em duas camadas:** Sprint 90a fez fix YAML + pre-check Python (cinto-e-suspensórios). Sprint-filha 90a-1 endurece causa raiz.

(o) **PII em revisor visual (4 sítios):** Sprint D2 mascara CPF/CNPJ em UI exibido (JSON), observação humana, blocos do relatório, e meta render -- todos os 4 sítios.

(p) **Supervisor valida pessoalmente, não despacha validador:** decisão recorrente do dono. Opus principal lê diff, roda proof-of-work, captura DEPOIS, julga APROVADO/RESSALVAS.

## Pendência humana registrada (memória `project_validacao_humana_pendente.md`)

Dono pediu textualmente: "to com a parte dos arquivos abertos e dos textos extraídos, mds é muita coisa pra arrumar. Ao final do projeto precisamos fazer essas validações juntos". Sessão dedicada de revisão homem-máquina via Revisor (Sprint D2) -- 760 arquivos pendentes, ~6.5h sessão Opus + supervisor par-a-par. Pré-requisito implícito antes da Fase OMEGA.

## Estado git ao final desta sessão

- Branch: `main`
- Último commit: `a48b843` (chore sprint 98 --executar)
- **Push parcial:** último push em `7cc4c68`. **9 commits ainda não pushed** após esse: `306d76c`, `d615488`, `52e7894`, `835f0a7`, `25fdb5b`, `84b071e`, `6f54feb`, `a48b843`, mais este handoff e atualizações de docs.
- Worktrees: limpos (todos os 4 da sessão removidos após cada sprint fechar).

## Como retomar amanhã

```bash
# 1. Garantir baseline saudável
cd /home/andrefarias/Desenvolvimento/protocolo-ouroboros
git status                # deve estar limpo (exceto .claude/)
git log --oneline -5      # último commit a48b843 ou superior
.venv/bin/pytest tests/ -q  # 1.620+ passed
make smoke                # 8/8
make lint                 # verde

# 2. Verificar grafo
sqlite3 data/output/grafo.sqlite "SELECT json_extract(metadata,'\$.tipo_documento'), COUNT(*) FROM node WHERE tipo='documento' GROUP BY 1;"
# Esperado: holerite=24, das_parcsn_andre=19, nfce=4, boleto=2, dirpf=1

sqlite3 data/output/grafo.sqlite "SELECT COUNT(*) FROM edge WHERE tipo='documento_de';"
# Esperado: 25

# 3. Listar próximas sprints
ls docs/sprints/backlog/
# 99 e 100 são P1 prontas; 95a/95b/95c/INFRA-D2a/90a-1 são P2/P3
```

## Próxima ação sugerida

A) **Push do que sobrou** (8 commits) -- requer aprovação explícita do dono.

B) **Rodar Sprint 99** (P1, redactor PII em logs, ~1h, pode ser solo ou em paralelo com 100).

C) **Rodar Sprint 100** (P1, deep-link tab dentro de cluster, ~2h).

D) **Sessão dedicada de validação humana via Revisor** (P0 humana). 760 arquivos pendentes. Pré-requisito antes de OMEGA. Não deve ser despachada para subagent -- é Opus + supervisor lado a lado.

## Arquivos de retomada canônica (mesma ordem do PROMPT_NOVA_SESSAO.md)

1. `contexto/POR_QUE.md`
2. `contexto/ESTADO_ATUAL.md` -- atualizado nesta sessão para refletir Fase NU fechada
3. `contexto/COMO_AGIR.md`
4. `CLAUDE.md` -- header v5.6, tabela da Fase NU executada
5. `docs/HANDOFF_2026-04-27_fase_nu_completa.md` (este arquivo)
6. `VALIDATOR_BRIEF.md` rodapé -- 7 padrões canônicos novos (j-p)

---

*"Saber onde paramos é metade do caminho de volta." -- princípio do handoff honesto*
