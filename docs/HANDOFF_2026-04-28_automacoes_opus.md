# HANDOFF 2026-04-28 -- Sessão Automações Opus

**Sessão:** 2026-04-28 (continuação direta da Sprint 103 fase Opus)
**HEAD final:** `59bc381` (Sprint 106a)
**Baseline pytest:** 1.917 -> **1.971 passed** (+54 testes em 1 sessão, zero regressão)
**Sprints concluídas em sequência:** 7 + 1 sub-sprint = 8 sprints

---

## Eventos por ordem cronológica

### Bloco 1 -- Sprint 103 fase Opus (commit `6009b00`)

Continuação direta da Sprint 103 já mergeada (commit `5614da9`). A fase técnica entregava UI 3-colunas e schema; faltava o **Opus de fato fazer ground-truth** lendo cada arquivo.

Pipeline:
1. `scripts/opus_extrair_transcricoes.py` -- itera as 29 pendências do Revisor, extrai texto via pdfplumber + tesseract, grava em `data/output/transcricoes_opus/transcricoes.json`.
2. Supervisor (Opus / Claude) lê cada transcrição e decide `valor_opus` para cada uma das 5 dimensões canônicas.
3. `scripts/opus_persistir_decisoes.py` -- aplica `salvar_marcacao(... valor_opus=<x>)` para cada par (item_id, dimensão). 145 marcações persistidas (29 × 5).
4. `scripts/popular_valor_etl_revisao.py` -- popula `valor_etl` em batch para que UI mostre 3 colunas de saída.

UI revisor.py ganhou:
- `extrair_valor_etl_para_dimensao(pendencia, dimensao)` -- mapeia metadata para 5 dimensões.
- `gerar_ground_truth_csv(caminho_db, caminho_csv)` -- exporta CSV 8 colunas + flag divergência.
- Cada dimensão exibe ETL/Opus/Humano lado-a-lado com marcador `:red[(diverge)]` quando ETL ≠ Opus.
- Botão "Exportar ground-truth CSV" no painel.
- Tabela "Comparação ETL × Opus" no topo do Revisor (44 divergentes de 145).

**Achados materiais da fase Opus** (origem das 5 sprints subsequentes):
1. 3 PDFs bit-a-bit Americanas em `_classificar/` -- residual da Sprint 97 page-split tentativo.
2. 4 holerites com `arquivo_origem` apontando para arquivos REMOVIDOS pela Sprint 98 `--executar` (na verdade 24 nodes ao varrer o grafo todo).
3. 2 NFCe Americanas em `data/raw/casal/` com CPF do Andre no cupom -- classifier antigo.
4. 2 cupons-foto OCR ilegível em `_conferir/`.
5. 13 DAS PARCSN com fornecedor=ANDRE em vez de Receita Federal.

### Bloco 2 -- Sprint INFRA-DEDUP-CLASSIFICAR (commit `598e723`)

Resolve achado #1. Helper `src/intake/dedup_classificar.py::deduplicar_classificar()` detecta sha256 idêntico e remove fósseis preservando canônico (sem sufixo `_<N>`).

**Runtime real:** 3 → 1 PDF (-2 fósseis sha 6c1cc203...).

CLI `scripts/dedup_classificar_lote.py` com `--dry-run` + `--executar`. 10 testes regressivos.

### Bloco 3 -- Sprint 98a (commit `6228c91`)

Resolve achado #2. `src/graph/backfill_arquivo_origem.py`:
- `detectar_paths_quebrados(grafo)` lista nodes onde `metadata.arquivo_origem` aponta para Path inexistente.
- `resolver_via_metadata(meta)` aplica heurísticas em ordem: holerite (mes_ref + razão social G4F/INFOBASE + desempate por líquido), DAS PARCSN (vencimento), genérico (rglob nome antigo).
- `backfill_arquivo_origem(grafo, dry_run)` atualiza metadata.

**Runtime real:** 24 paths quebrados → 0. Aplicado via `scripts/backfill_arquivo_origem_lote.py --executar`.

### Bloco 4 -- Sprint 105 (commit `ab9d5de`)

Resolve achado #3. Migração `data/raw/casal/` → `data/raw/<pessoa>/` quando CPF/CNPJ/razão no conteúdo identifica pessoa específica.

Mudança em `src/intake/pessoa_detector.py::_casar_via_pessoas_yaml`:
- **Nova camada CPF (PRIMEIRA)** antes de CNPJ. Lê `cpfs` do `mappings/pessoas.yaml`.
- Fecha gap quando `mappings/cpfs_pessoas.yaml` (mapping antigo) não existe.
- Hash mascarado no log (LGPD-safe via `hash_curto_pii`).

`scripts/migrar_pessoa_via_cpf.py`:
- Itera `data/raw/casal/`, extrai texto via pdfplumber+OCR fallback.
- Chama `detectar_pessoa()`. Se retorna `andre` ou `vitoria`, move arquivo preservando subpasta + atualiza `metadata.arquivo_origem` do node.

**Runtime real:** 6 → 3 arquivos casal/ (-3 migrados: 1 NFCe + 2 garantias estendidas, todos via CPF do Andre no OCR).

### Bloco 5 -- Sprint 107 (commit `b470024`)

Resolve achado #5. `mappings/fornecedores_sinteticos.yaml` declara entidades fiscais canônicas (RECEITA_FEDERAL CNPJ 00.394.460/0001-41, INSS CNPJ 29.979.036/0001-40) com `aplica_a_tipos`.

`src/graph/ingestor_documento.py`:
- `_carregar_fornecedores_sinteticos()` cache em módulo (lookup invertido tipo → sintético).
- `ingerir_documento_fiscal()` agora troca `cnpj_emitente` + `razao_social` pelo sintético quando tipo casa, preservando contribuinte original em `metadata.contribuinte`.

**Migração de 13 DAS PARCSN existentes:** acontece via `./run.sh --reextrair-tudo` (Sprint 104). Codificação pronta.

### Bloco 6 -- Sprint 106 (commit `a05ebdb`)

Resolve achado #4. `src/intake/ocr_fallback_similar.py`:
- `buscar_similar(arquivo, grafo, tipo)` combina `phash` (50%) + `temporal` (30%) + `textual` (20%); threshold `confidence_minima` 0.70.
- Graceful degradation: phash via `imagehash` (opcional); pesos reescalam quando lib ausente.
- `reanalisar_pasta_conferir(grafo, dry_run)` itera `_conferir/` e tenta fallback.

**Runtime real:** motor ativo, mas critério original de legibilidade (chars úteis < 50) não capturava garbage do Tesseract -- gerou Sprint 106a.

### Bloco 7 -- Sprint 108 (commit `18a58d8`)

Orquestração das 5 automações em `run.sh`.

Helper `run_passo()`:
- Loga início/fim/duração em `logs/auditoria_opus.log`.
- Falha-soft (smoke aritmético final captura regressão).

`--full-cycle` agora encadeia:
```
inbox -> dedup_classificar -> migrar_pessoa_via_cpf -> backfill_arquivo_origem -> pipeline-tudo
```

`--reextrair-tudo` agora encadeia:
```
confirmação -> [3 automações] -> reprocessar_documentos --forcar-reextracao
```

Menu interativo opção 7 "Auditoria Opus completa" delega para `--reextrair-tudo`.

`docs/AUTOMACOES_OPUS.md` documenta a cadeia.

### Bloco 8 -- Sprint 106a (commit `59bc381`)

Refina critério de legibilidade descoberto durante validação real da Sprint 106.

Critério composite (qualquer um dispara ilegível):
1. chars úteis < limiar (existente).
2. **palavras conhecidas em PT-BR < N** (novo) -- whitelist domínio-específica (substantivos fiscais/financeiros, ZERO preposições curtas que aparecem por acaso em garbage).
3. **ratio non-letras > limite** (novo) quando total > 100 chars.

`mappings/ocr_fallback_config.yaml` ganhou parâmetros `min_palavras_conhecidas_por_tipo` (default 8) e `max_ratio_non_letras_por_tipo` (default 0.45).

**Runtime real:** 2/2 cupons-foto detectados como ilegíveis (vs 0/2 antes).

---

## Métricas finais

| Métrica | Antes (5614da9) | Depois (59bc381) | Delta |
|---|---|---|---|
| pytest | 1.917 passed | **1.971 passed** | **+54** |
| Sprints concluídas | 113 | **122** | +9 |
| PDFs duplicados em _classificar/ | 3 | **1** | -2 fósseis |
| Paths quebrados no grafo | 24 | **0** | -100% |
| Arquivos casal/ ambíguos | 6 | **3** | -3 (via CPF) |
| Pendências Revisor | 29 | **27** | -2 |
| `make lint` | exit 0 | **exit 0** | -- |
| `make smoke` | 8/8 + 23/23 | **8/8 + 23/23** | -- |

---

## Padrões canônicos descobertos/consolidados

(q) **Automacao no fluxo canonico OU não está resolvido.** Lições da fase Opus que viraram operação manual repetida são falsas conclusões. Sprint 108 (helper `run_passo`) é o ponto que transforma achado em invariante. A regra "automação no `--full-cycle` OU não está resolvido" merece ir para VALIDATOR_BRIEF.

(r) **Fornecedor sintético para entidades fiscais.** `mappings/fornecedores_sinteticos.yaml` declara RECEITA_FEDERAL/INSS com CNPJ oficial. Documentos casam por `tipo_documento`. Contribuinte preservado em `metadata.contribuinte`. Refactor schema-only que migra via Sprint 104 reextração.

(s) **Critério de legibilidade composite.** Chars úteis + palavras conhecidas em PT-BR + ratio non-letras. Whitelist domínio-específica (substantivos fiscais/financeiros). Preposições curtas removidas porque aparecem por acaso em garbage Tesseract.

(t) **Backfill heurístico por mes_ref + razão social + valor.** Paths quebrados pós-rename retroativo são recuperáveis via metadata em vez de rerodar pipeline inteiro. Heurística por tipo (holerite vs DAS) + desempate por valor líquido.

(u) **Camada CPF antes de CNPJ no pessoa_detector.** `pessoas.yaml` (Sprint 90) já declarava CPFs mas `_casar_via_pessoas_yaml` ignorava -- só usava CNPJ/razão/alias. Sprint 105 fechou o gap. Hash mascarado para LGPD.

---

## Backlog aberto pós-rodada Opus

### P3 (16 specs, não-bloqueantes)

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

### Pré-OMEGA

- Sessão humana de validação via Revisor (27 pendências, ~3-4h Opus + supervisor par-a-par).
- Reextração em volume (`./run.sh --reextrair-tudo`) para migrar 13 DAS PARCSN para `RECEITA_FEDERAL` + atualizar metadata Sprint 95a (líquido).

---

## Próximos passos imediatos para o dono

1. **Validar visualmente** as 3-colunas do Revisor: `./run.sh --dashboard` → cluster Documentos → aba Revisor.
2. **Marcar OK/Erro/N-A** em pelo menos 5 pendências (validar fluxo humano).
3. **Exportar CSV** ground-truth (botão na linha de ações).
4. **Rodar `--reextrair-tudo`** (opção 7 do menu) para migrar 13 DAS PARCSN.
5. **Inspecionar `logs/auditoria_opus.log`** após qualquer `--full-cycle` para ver duração de cada passo.

---

## Arquivos-chave criados/modificados nesta rodada

### Código

- `src/intake/dedup_classificar.py` (NOVO, ~120L) -- INFRA-DEDUP.
- `scripts/dedup_classificar_lote.py` (NOVO, ~50L) -- CLI.
- `src/graph/backfill_arquivo_origem.py` (NOVO, ~210L) -- Sprint 98a.
- `scripts/backfill_arquivo_origem_lote.py` (NOVO, ~55L) -- CLI.
- `scripts/migrar_pessoa_via_cpf.py` (NOVO, ~210L) -- Sprint 105.
- `src/intake/ocr_fallback_similar.py` (NOVO, ~330L) -- Sprint 106 + 106a.
- `src/intake/pessoa_detector.py` (modificado) -- camada CPF (Sprint 105).
- `src/graph/ingestor_documento.py` (modificado) -- fornecedor sintético (Sprint 107).
- `run.sh` (modificado) -- helper `run_passo` + automações encadeadas (Sprint 108).
- `scripts/menu_interativo.py` (modificado) -- opção 7 (Sprint 108).
- `src/dashboard/paginas/revisor.py` (modificado) -- 3-colunas + helper extrair_valor_etl + export CSV (Sprint 103 fase Opus).

### Configuração

- `mappings/fornecedores_sinteticos.yaml` (NOVO) -- Sprint 107.
- `mappings/ocr_fallback_config.yaml` (NOVO) -- Sprint 106 + 106a.

### Scripts auxiliares (Opus runtime)

- `scripts/opus_extrair_transcricoes.py` (NOVO) -- extrai transcrição cua de cada pendência.
- `scripts/opus_persistir_decisoes.py` (NOVO) -- aplica decisões Opus no DB.
- `scripts/popular_valor_etl_revisao.py` (NOVO) -- popula valor_etl em batch.

### Testes

- 6 arquivos novos: ~75 testes regressivos.

### Documentação

- `docs/AUTOMACOES_OPUS.md` (NOVO) -- doc canônico das 5 automações.
- `docs/sprints/concluidos/sprint_*.md` -- 7 specs movidas de backlog.
- `data/output/transcricoes_opus/transcricoes.json` -- 29 pendências com texto OCR.
- `data/output/transcricoes_opus/decisoes_opus.json` -- 29 decisões Opus por dimensão.

---

## Estado git final

- Branch: `main`
- Último commit: `59bc381` (Sprint 106a)
- Origin/main sincronizado.
- Worktrees: limpos.

---

*"Cinco achados isolados não são uma sprint -- são uma cadeia. A Sprint 108 fechou a cadeia." -- princípio do invariante automatizado*
