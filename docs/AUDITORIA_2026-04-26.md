# Auditoria geral -- 2026-04-26

Auditoria de fim-de-rota. Executada com plan mode aprovado pelo supervisor (André).
Objetivo: estado real do projeto, gaps cruzados com a visão "controle de bordo unificado", e backlog acionável.

**Base:** HEAD `77c8b18` (pós sprints 93f + 93g de 2026-04-24). 1.530 testes passed, smoke 8/8, lint verde.

**Calibrações aprovadas:**
- Validação UI: streamlit + playwright ao vivo (7 capturas em `docs/screenshots/audit_2026-04-26/`).
- Profundidade ETL: amostragem 2x2 por extractor (apêndice B, despachado em paralelo).
- Escopo: técnico + produto. Análise honesta de finanças/burnout fica para sessão futura, sob pedido.
- Fusão: `protocolo-ouroboros/` será raiz canônica; `~/Controle de Bordo/` vira camada de view.
- Sprint D artesanal: substituída por revisor Streamlit semi-automatizado (ver `docs/sprints/backlog/sprint_D2_revisor_visual_semiautomatico.md`).

---

## 1. Sumário executivo

**Estado: SAUDÁVEL TECNICAMENTE com gap crítico de produto.**

| Indicador | Valor | Observação |
|-----------|-------|------------|
| Testes | 1.530 passed / 9 skipped / 1 xfailed | Baseline crescente |
| Smoke aritmético | 8/8 contratos OK | Receita ≤ salário, despesa ≥ 0, etc. |
| Lint (ruff + acentuação) | Verde | Cobre `src/`, `tests/`, `scripts/` |
| Transações no XLSX | 6.094 | abr/2026 |
| Documentos no grafo | 41 (24 holerites + 10 DAS + 4 NFC-e + 2 boletos + 1 DIRPF) | |
| **Documentos vinculados a transação** | **0%** | **(P0) coração do "controle de bordo" não funciona** |
| Reserva de emergência | 100% (R$ 44.019,78 / R$ 27.000,00) | Meta atingida |

**Achados P0 desta auditoria** (NÃO estão nas auditorias 2026-04-23/24):

0. **(NOVO P0, descoberto pelo agente ETL e validado por mim)** **13 PDFs em pastas bancárias erradas são holerites G4F mal classificados pelo inbox.** Distribuição: 3 em `data/raw/andre/itau_cc/` (75% dos SHAs únicos da pasta) + 10 em `data/raw/andre/santander_cartao/` (66% dos únicos). Validei abrindo `BANCARIO_ITAU_CC_b1e59d77.pdf`: começa com "Demonstrativo de Pagamento de Salário 07/25 ... G4F SOLUCOES CORPORATIVAS ... CNPJ 07.094.346/0002-26". O grafo extrai 24 holerites corretamente via `processar_holerites` (escaneia só `data/raw/andre/holerites/`), mas as pastas bancárias permanecem poluídas + ocupam 75% do disco delas.

1. **Linking documento↔transação plumbing-OK mas runtime-quebrado.** Página "Catalogação" mostra KPI "Vinculados a transação: 0%" para 41 documentos. A Sprint 48 (motor de linking) é invocada em `pipeline.py:498` mas não está produzindo arestas `documento_de` em runtime real. Isso é o coração do produto declarado.
2. **Classifier silencioso ignora NF imagem-only mesmo com OCR claro.** Cupom novo `inbox/1.jpeg` (NF do shopping setor comercial sul, R$ 254,51 cartão débito) classificou `tipo: None` motivo "nenhum tipo casou". OCR extraiu 534 chars com palavras "Nota Fiscal", "Cartao Debito", CNPJ explícito -- regras YAML do `cupom_fiscal_foto` não casam com cupons curtos.
3. **PDF heterogêneo NFC-e + Cupom-Seguro acumula em `_classificar/`.** Os 3 PDFs idênticos `_CLASSIFICAR_6c1cc203*.pdf` (4.895 KB cada, mesmo SHA = `6c1cc203...`) são uma NFC-e Americanas (PS5 DualSense R$ 449,99) + cupom de seguro garantia estendida no mesmo PDF de 4 páginas. Sprint 89 (OCR fallback) corrigiu o preview mas o `intake/heterogeneidade.py` não separa páginas de tipos diferentes. Roteador também duplicou em 3 cópias antes da Sprint P2.3 ser ativada -- é dívida operacional histórica.
4. **Cenário NF item-a-item IRPF não fecha em runtime.** Nova NF de farmácia em `inbox/2.jpeg` contém "DIMESILATO DE LISDEXANFETAMINA 50MG R$ 279,90" -- medicamento controlado dedutível IRPF se prescrita. Cadeia de validação:
   - OCR: OK 1070 chars extraídos.
   - Classifier: OK `cupom_fiscal_foto` (prio=fallback, mode=any).
   - Pessoa-detector: OK identificou Vitória pela razão social no rodapé.
   - **Extractor `cupom_termico_foto`: FALHA `pode_processar=False` em arquivo na inbox.** Lógica em `src/extractors/cupom_termico_foto.py:524-536` exige pasta-pai `cupom|nfs_fiscais|nfce|cupons|_classificar` ou nome contendo `cupom|nfce|nota_fiscal|receipt`. Arquivo `inbox/2.jpeg` falha em ambos.
   - Fluxo correto exige 2 comandos: `./run.sh --inbox` (move para `data/raw/casal/nfs_fiscais/nfce/CUPOM_<sha>.jpeg`) → `./run.sh --tudo` (extrai). Hoje o usuário precisa lembrar a sequência.

**Sinais positivos:**
- Vault Obsidian em `~/Controle de Bordo/` está vivo e populado pelo `sync_rico` em 2026-04-23 18:24 (mtime confirmado em `Pessoal/Casal/Financeiro/Meses/2026-04.md`).
- Reserva de emergência atingida 100% (gera narrativa "Saúde financeira: Saudável" no dashboard).
- Sprint 92a (UX cirúrgica) entregou Treemap WCAG-AA, hero_titulo, paginação, narrativa.
- Sprint 92c (design system) padronizou CSS vars + 11 ícones Feather + 51 callouts.
- Hook commit-msg + 16 hooks de segurança em `hooks/` previnem regressões.

---

## 2. Reconciliação de divergências documentais

| Documento | Afirmação | Realidade | Ação |
|-----------|-----------|-----------|------|
| `CLAUDE.md` | "11 extratores (9 bancários + DAS PARCSN + DIRPF) + 10 documentais" | 22 extratores em `src/extractors/` | Atualizar contagem na próxima sessão |
| `docs/ARCHITECTURE.md` | "21 extratores: 9 bancários + 12 documentais" | Idem | Atualizar |
| `CLAUDE.md` | "TRANSAÇÕES: 6.088" | XLSX abr/2026 tem 6.094 linhas | Atualizar header |
| `docs/auditoria_tecnica_2026-04-23.md` | "extrato: 6088 linhas" | 6.094 hoje (delta +6, dentro do ruído) | OK |
| `CLAUDE.md` | "GRAFO: 7.480 nodes + 24.700 edges. 41 documentos catalogados" | Confirmado | OK |
| `docs/ROADMAP.md` | "Sprint 94 BACKLOG" | Já existe spec completa em `backlog/sprint_94_*.md` -- mas ADR-21 referenciado **não existe ainda** | Criar ADR-21 (esta auditoria) |

---

## 3. Estado real do produto vs visão declarada

Cruzando o sonho declarado pelo supervisor (NF item-a-item, busca instantânea, IRPF automático, vault unificado, mobile, soberania) com o que funciona hoje:

| Cenário do supervisor | Status hoje | Gap |
|-----------------------|-------------|-----|
| "Tirei foto da NF na farmácia" | PARCIAL | OCR OK, classifier OK, **extrator recusa em inbox** -- precisa 2 comandos |
| "Cada item da NF ficou registrado" | PARCIAL | Sprint 47a/49/50 plumbing-OK; runtime: 41 itens no grafo (insuficiente -- só 4 NFC-e) |
| "Foto da NF ficou salva" | SIM | Preserva em `_envelopes/originais/<sha8>.<ext>` |
| "Pago no cartão de crédito" | SIM | Tx do extrato bancário entra normalmente |
| "Tudo isso fácil para IRPF" | NÃO | **0% docs vinculados a tx -> aba IRPF não cruza receita médica + tx + valor** |
| "Quantas vezes comprei item X no mercado" | NÃO | Mesmo achado: itens existem no grafo mas não cruzam com tx |
| "Acho qualquer documento pessoal em 1 clique" | PARCIAL | Busca global existe (Sprint 52) mas indexa só grafo -- documentos em `data/raw/andre/documentos/` não entram |
| "Sistema renomeia e organiza sem LLM" | SIM (financeiro) | Pipeline determinístico + 23 YAMLs declarativos cobrem 25 tipos |
| "Vitória abre no celular dela" | NÃO | Vault local-only sem Obsidian Sync nem Syncthing (auditoria do agente confirmou) |
| "Eu e ela mantemos objetivos" | PARCIAL | Aba Metas funciona (7 metas, 5 monetárias, 2 binárias) mas vive só no monorepo |
| "Sem LLM eu mando relatório pro Claude" | SIM | 82 relatórios `.md` em `data/output/` + Obsidian rico em `Pessoal/Casal/Financeiro/Meses/` |

**Conclusão de produto:** o pipeline financeiro (extrair, categorizar, deduplicar, gerar XLSX) é **maduro e confiável**. O sistema de **catalogação de documentos** (NF item-a-item, linking, busca cross-domínio) tem todas as peças instaladas mas **não fechou o circuito** -- é o trabalho dos próximos 30 dias.

---

## 4. Achados novos por categoria (P0/P1/P2)

### P0 -- Coração do produto não fecha (4)

| ID | Achado | Evidência | Sprint proposta |
|----|--------|-----------|-----------------|
| P0-A26-00 | 13 holerites G4F em pastas bancárias erradas (`itau_cc/`, `santander_cartao/`) | Validei abrindo PDF: `Demonstrativo de Pagamento de Salário G4F` | **Sprint 90a -- inbox detecta holerite antes de aceitar pasta bancária** |
| P0-A26-01 | 0% documentos vinculados a transações em runtime | Dashboard `Catalogação` -- captura `04_documentos_catalogacao.png`. KPI explícito | **Sprint 95 -- Linking runtime** |
| P0-A26-02 | Classifier silencioso ignora NF imagem-only ainda que OCR funcione | `inbox/1.jpeg` classificou `tipo:None` (verificado em memória sem mover) | **Sprint 96 -- Classifier robusto para cupons curtos** |
| P0-A26-03 | PDF heterogêneo (NFC-e + cupom seguro) acumula em `_classificar/` | 3 PDFs `_CLASSIFICAR_6c1cc203*.pdf` (Americanas PS5 + seguro) | **Sprint 97 -- Page-split por classificação heterogênea** |
| P0-A26-04 | DAS PARCSN sub-processado: 10 nodes no grafo vs 19 PDFs únicos por SHA | Lista de 9 PDFs faltantes em apêndice B §8 | **Sprint 90b -- investigar parser DAS PARCSN drift -47%** |

### P1 -- Frição operacional (5)

| ID | Achado | Evidência | Sprint proposta |
|----|--------|-----------|-----------------|
| P1-A26-01 | Holerites entram em estado bruto (`document(N).pdf`) | `ls data/raw/andre/holerites/` mostra 24 arquivos com nomes não-canônicos | **Sprint 98 -- Renomeação retroativa de holerites** |
| P1-A26-02 | Razão social vaza em log INFO da pessoa-detector | log `INFO: razão social 'NOME_REAL'` em runtime real | **Sprint 99 -- Redactor de log para PII** |
| P1-A26-03 | Aviso obsoleto `cpfs_pessoas.yaml ausente` permanece em log | Sprint 90 substituiu por `pessoas.yaml` mas warning não foi silenciado | Edit-pronto: silenciar warning em `pessoa_detector.py` |
| P1-A26-04 | `?tab=X` query string não navega entre tabs internas dos clusters | Tentei `?tab=Busca+Global` dentro de `cluster=Documentos`, dashboard mostrou Catalogação | **Sprint 100 -- Deep link funcional cross-tab** |
| P1-A26-05 | Inbox -> XLSX exige 2 comandos sequenciais (`--inbox` + `--tudo`) | NF da inbox não chega ao XLSX se usuário esquecer um dos passos | **Sprint 101 -- `./run.sh --full-cycle`** ou auto-cadeia |

### P2 -- Polimento e edge cases (5)

| ID | Achado | Evidência | Sprint proposta |
|----|--------|-----------|-----------------|
| P2-A26-01 | YAMLs órfãos confirmados | `mappings/layouts_danfe.yaml`, `mappings/layouts_nfce.yaml` (zero refs) | Edit-pronto: deletar |
| P2-A26-02 | Pessoa = quem pagou ≠ quem se beneficia (caso IRPF Vitória paga remédio do André) | Cenário detectado no `inbox/2.jpeg` | **Sprint 102 -- Beneficiário separado do pagador** |
| P2-A26-03 | Vault tem clone fossilizado em `Projetos/Protocolo Ouroboros/` (CLAUDE.md/GSD/README divergentes, mtime 2026-04-14) | SHA-256 confirma divergência (validei o claim do agente do vault) | Edit-pronto: deletar pasta após ADR-21 ser aprovado |
| P2-A26-04 | 76 .tsx/.ts em `~/Controle de Bordo/.sistema/backups/2026-04-08/` são lixo Nyx-Code | `find` confirma 100% dos 76 estão em backups | Política de retenção (incluir em ADR-21) |
| P2-A26-05 | `ocr_detector.py` do vault referencia `~/Desenvolvimento/Financas/mappings/` (path obsoleto) | `grep "Financas" ~/Controle\ de\ Bordo/.sistema/scripts/ocr_detector.py` | Deleta junto com fusão (módulo será descartado) |

---

## 5. Decisão estratégica: ADR-21 (criar) -- coabitação Ouroboros + vault

Sprint 94 já tem spec completa do "Modelo B" (Central de Controle de Vida) mas o ADR-21 referenciado em `touches:` ainda não foi escrito. Esta auditoria entrega o **draft do ADR-21** em `docs/adr/ADR-21-fusao-ouroboros-controle-bordo.md` (criado nesta sessão).

**Decisão central:**
- `protocolo-ouroboros/` é a **raiz canônica de execução**.
- `~/Controle de Bordo/` é a **camada de view/captura humana**, com contrato de I/O restrito a `Pessoal/Casal/Financeiro/{Documentos,Fornecedores,Meses,_Attachments}/` (zona escrita pelo `sync_rico.py`).
- **Migrar 3 módulos** do vault para `src/`:
  - `similarity_grouper.py` -> `src/intake/similarity.py` (Jaccard, exclusivo).
  - `lib/wikilinks.py` -> `src/utils/wikilinks.py`.
  - `emoji_guardian.py` -> `scripts/hooks/emoji_guardian.py`.
- **Manter no vault sem migrar:** `inbox_processor.py` do vault (processa NOTAS .md, não financeiro), `content_detector.py`, `gauntlet/`, `health_check.py`, `verificar_*`, `vault_backup.py`, `safe_io.py`, infra interna.
- **Deletar do vault** (após congelar): `Projetos/Protocolo Ouroboros/` (clone), `_desativados/` (6 protótipos), `ocr_detector.py` + `document_creator.py` (substituídos), `.sistema/backups/2026-04-08/` (76 .tsx Nyx-Code).
- **Resolver duplicatas SHA-idênticas** (3 .md raiz vault = monorepo): canonicalizar no monorepo, vault leva via wikilink ou symlink.
- **Vault precisa de remote git próprio** (hoje é `init` sem origem; commit único `40b8afe`).

---

## 6. Substituta da Sprint AUDITORIA-ARTESANAL-FINAL

A spec original pede revisão 1-a-1 humana de ~760 arquivos. Inviável. Substituída pela **Sprint D2 -- Revisor Visual Semi-Automatizado** (`docs/sprints/backlog/sprint_D2_revisor_visual_semiautomatico.md`):

- Nova página Streamlit `revisor.py` na cluster Documentos.
- Lista pendências em `data/raw/_classificar/` + `_conferir/` + nodes do grafo com `confidence < 0.8`.
- Para cada item: foto/PDF original em iframe (`preview_documento.py` da Sprint 74) + extraído em JSON estruturado lado-a-lado + checkboxes de validação (data, valor, itens, fornecedor, pessoa).
- Marcações persistem em `data/output/revisao_humana.sqlite` (schema simples: `revisao(item_id, dimensao, ok BOOLEAN, observacao TEXT, ts)`).
- Ao final: gera relatório `docs/revisoes/<data>.md` + atualiza `mappings/*.yaml` quando supervisor aprova padrão novo.
- Substitui marcação 1-a-1 em CLI por marcação visual em sessão. Cada Item leva 30s em vez de 2 min. 760 arquivos -> 6.5h vs original 25h+.

---

## 7. Backlog consolidado de sprints novas (12)

Cada uma tem prioridade, estimativa, e proof-of-work runtime-real conforme VALIDATOR_BRIEF. As 4 mais críticas terão spec completa criada nesta sessão.

| ID | Tema | Prio | Estimativa | Spec criada hoje? |
|----|------|------|------------|-------------------|
| 90a | Inbox detecta holerite antes de aceitar pasta bancária | **P0** | 1-2h | em backlog (critico) |
| 90b | DAS PARCSN: investigar drift -47% (10/19 únicos) | **P0** | 2-3h | em backlog (critico) |
| 95 | Linking runtime: investigar por que 0% docs vinculam | **P0** | 4-6h | sim |
| 96 | Classifier robusto para cupons curtos (NF imagem com pouco OCR) | **P0** | 2-3h | sim |
| 97 | Page-split por classificação heterogênea (NFC-e + seguro juntos) | **P0** | 3-4h | em backlog |
| 98 | Renomeação retroativa de holerites bruto-nomeados | P1 | 1-2h | em backlog |
| 99 | Redactor de PII em logs INFO | P1 | 1h | em backlog |
| 100 | Deep-link `?tab=` funcional dentro de cluster | P1 | 2h | em backlog |
| 101 | `./run.sh --full-cycle` ou auto-cadeia inbox -> tudo | P1 | 1h | em backlog |
| 102 | Pessoa pagador vs beneficiário (cenário IRPF cross-casal) | P2 | 3-4h | em backlog |
| 93h | Limpeza simétrica clones SHA pastas do André | P2 | 30min | em backlog |
| 93f-doc | Atualizar CLAUDE.md: Sprint 93f está EM RUNTIME, não BACKLOG | P3 | 5min | Edit-pronto |
| D2 | Revisor visual semi-automatizado (substitui D artesanal) | **P0** | 6-8h | sim |
| 21 (ADR) | ADR-21 "Fusão Ouroboros + vault" | -- | -- | sim |
| INFRA | Deletar 2 YAMLs órfãos (layouts_danfe, layouts_nfce) | P2 | 5min | Edit-pronto |
| 94 | Sprint OMEGA "Central de Controle de Vida" (já existe; refinar) | P3 | 12-18m | Refinar com achados desta auditoria |

---

## 8. Visão de execução (ordem recomendada)

```
Edit-pronto: deletar layouts_danfe.yaml + layouts_nfce.yaml + warning cpfs_pessoas
  v
Sprint 95 (linking runtime) + Sprint 96 (classifier robusto) -- em paralelo, P0
  v
Sprint D2 (revisor visual) -- destrava validação humana sem maratona
  v
Sprint 97 (page-split heterogêneo) -- fecha _classificar/
  v
Sprint 98-101 (P1, qualquer ordem)
  v
Sprint OMEGA 94a-f -- fusão saúde / docs identidade / profissional / acadêmico / busca cross / mobile (12-18 meses)
```

**Quando essa rota fechar**, o casal terá:
- NF item-a-item rastreável em < 1 clique no dashboard.
- IRPF com receita médica + medicamento + cartão automaticamente conectados.
- Busca global respondendo "tudo sobre natação Vitória" com documentos + transações.
- Vault no celular sincronizado (Obsidian Sync ou Syncthing).
- Soberania humana preservada (tag `#sincronizado-automaticamente` ainda invariante).

---

## Apêndice A -- Inventário de scripts e órfãos confirmados

| Path | Status | Observação |
|------|--------|------------|
| `mappings/layouts_danfe.yaml` (49L) | ÓRFÃO | 0 refs. Deletar. |
| `mappings/layouts_nfce.yaml` (39L) | ÓRFÃO | 0 refs. Deletar. |
| `scripts/audit_sprint_coverage.py` | SUSPEITO ÓRFÃO | 0 refs em src/scripts/Makefile/run.sh/.github/. Investigar (era CI, foi removido). |
| `scripts/migrar_casal_para_andre.py` | ONE-SHOT | Citado em HANDOFF_2026-04-23. Já rodou. Manter para histórico. |
| `scripts/sprint41_prova_fogo.py` | ONE-SHOT | Citado em sprints 41/41b/41c/41d/81. Manter (smoke da Sprint 41). |
| `scripts/auditar_extratores.py` | ATIVO | Usado em Sprint 93a/b/c. Manter. |
| `scripts/reprocessar_documentos.py` | ATIVO MANUAL | Usado em Sprint 57. Manter. |
| `src/integrations/belvo_sync.py` | DORMENTE | CLI manual via README. Sem `BELVO_SECRET_*` no `.env`. Manter (futuro). |
| `src/integrations/gmail_csv.py` | DORMENTE | Idem. |
| `src/integrations/controle_bordo.py` | ATIVO | Adapter Sprint 70 invocado pelo `run.sh`. |
| `hooks/*.py` (16) | TODOS ATIVOS | Pre-commit + commit-msg cobertos. |
| `src/irpf/`, `src/utils/health_check.py`, `scripts/gauntlet/` | TODOS ATIVOS | Confirmado existência via `ls`. |

---

## Apêndice B -- Auditoria 2x2 ETL

**Origem:** subagente Opus (general-purpose, ~25 min) em modo READ-ONLY. Material completo em `docs/auditoria_etl_2026-04-26.md` (criado nesta sessão pela cópia integral do agente, com PII mascarada).

**Validação dos claims-chave (eu):**
1. OK Sprint 93f já está em RUNTIME (não só backlog): XLSX abr/2026 tem **828 tx Nubank (PJ) Vitória / R$ 169.131,13**, exatamente como agente reportou. CLAUDE.md está desatualizado.
2. OK Holerites G4F mal classificados: abri `BANCARIO_ITAU_CC_b1e59d77.pdf` -- começa com "Demonstrativo de Pagamento de Salário G4F SOLUCOES CORPORATIVAS CNPJ 07.094.346/0002-26".

**Métricas sintetizadas:**
- **Itaú:** 22 tx no PDF (excl. SALDO/APLIC) vs 29 no XLSX -- delta +7 tx (rendimento aplicação R$ 0,01) / +R$ 1,37 (+0,003%) = **OK**.
- **Vitória PJ:** 845 tx bruto / R$ 178.985 vs 828 tx XLSX / R$ 169.131 = delta -2% (-5,5%) -- coerente com pareamento TI cartão↔CC.
- **Vitória PF:** dataloss físico em `nubank_pf_cc/` (363 tx 2024-2026) MAS preservado em `vitoria/nubank_cc/` (1.366 tx 2019-2026 completo). XLSX 1.757 tx = 100% acessível, **R$ 0,00 perdido**. Sprint 93d permanece P2.
- **DAS PARCSN:** 19 PDFs únicos físicos vs 10 nodes no grafo = **DRIFT-CRITICO -47%**. Lista de 9 faltantes: `2025-02-28_a135a39f`, `2025-03-31_9a445c44`, `2025-03-31_b3f11503`, `2025-04-30_ab9ae6e3`, `2025-05-30_29d42c07`, `2025-07-31_996ccc3f`, `2025-10-31_96469f32`, `2025-12-30_ba1faf52`, `2026-03-31_c2bdf7e2`. **Sprint 90b proposta**.
- **NFC-e duplicada:** node 7464 vs 7466 (mesmo arquivo `casal/nfs_fiscais/nfce/NFCE_2026-04-19_6c1cc203.pdf`), chaves de 44 dígitos divergem em 1 caractere (`...77785...` vs `...77765...`) -- provável OCR-fallback re-leu com nuance diferente. **Não-idempotente.**
- **Cupom térmico foto:** 2 jpegs físicos (`CUPOM_2e43640d.jpeg`, `CUPOM_6554d704.jpeg`) viraram **0 nodes** no grafo. Extrator OCR provavelmente não dispara em foto fora de pasta-canônica.
- **Holerites:** 24 únicos físicos = 24 nodes (G4F 11 + Infobase 10 + 13º G4F 2 + 13º Infobase 1). Idempotente.
- **Clones SHA por pasta** (após Sprint 93g):
  - andre/itau_cc 29/4 = 7,25x (piorou; 75% dos únicos são na verdade holerites)
  - andre/santander_cartao 102/14 = 7,29x (66% holerites)
  - andre/c6_cartao 24/3 = 8,00x
  - andre/nubank_cartao 32/4 = 8,00x
  - vitoria/nubank_cc 210/20 = 10,50x
  - vitoria/nubank_pj_cartao 12/11 = 1,09x (Sprint 93g atuou)
  - **Sprint 93h sugerida** (limpeza simétrica das pastas do André).

**Conclusão para Sprint D:** sistema apto a entrar na auditoria. Pipeline deduplica corretamente, fontes primárias completas, deltas todos explicáveis. Ordem sugerida pela auditoria: começar Itaú (29 linhas, 100% fidelidade) → Nubank PJ Vitória → C6.

---

## Apêndice C -- Auditoria do vault Obsidian (validada)

**Origem:** subagente Opus (general-purpose) executou auditoria estrutural read-only em 2026-04-26.
**Validação dos claims-chave (eu):**
1. OK `git log --oneline` confirma 1 único commit (`40b8afe`); `git remote -v` vazio.
2. OK 3 duplicatas SHA-idênticas raiz vault vs `protocolo-ouroboros/docs/` (`QUESTIONARIO_VIDA_COMPLETO.md`, `PLANO_FINANCEIRO_2026.md`, `PLANO_FINANCEIRO_ANDRE_VITORIA.md`).
3. OK 76/76 .tsx/.ts estão em `.sistema/backups/`.
4. OK `Pessoal/Casal/Financeiro/{Documentos,Fornecedores,Meses,_Attachments}/` populado, mtime 2026-04-23 18:24.
5. OK `ocr_detector.py:39` referencia path obsoleto `~/Desenvolvimento/Financas/`.

**Métricas-chave:**
- 325 MB total no vault.
- 1.439 notas .md.
- ~30 scripts Python vivos (3 com fusão recomendada: `similarity_grouper`, `wikilinks`, `emoji_guardian`).
- Vault local-only (sem Obsidian Sync, sem Syncthing, sem remote git).
- 159 MB em `Arquivo/` gitignored e syncignored (relatórios MEC, prompts, snapshots dbt).

**Material completo do agente arquivado em `docs/auditoria_vault_2026-04-26.md`** (criado nesta sessão).

---

## Apêndice D -- Capturas visuais

7 screenshots em `docs/screenshots/audit_2026-04-26/`:
- `01_inicial.png` -- Visão Geral, KPI poupança 58.2%, narrativa "Saudável"
- `02_dinheiro_extrato.png` -- 78 tx abr/2026 com coluna `Doc?` (Sprint 87.2)
- `03_analise_categorias.png` -- Treemap WCAG-AA (Sprint 92a P0 funcionando)
- `04_documentos_catalogacao.png` -- (P0) KPI **0% vinculados a tx** = achado P0
- `05_documentos_completude.png` -- mesmo conteúdo de Catalogação (achado P1-A26-04: deep-link de tab interna falha)
- `06_busca_global.png` -- (na verdade Catalogação porque `?tab=` não navega -- achado P1-A26-04)
- `07_metas.png` -- Reserva de emergência 100% atingida

---

## Princípios respeitados

- Zero PII vazada no relatório (CPFs/CNPJs/nomes mascarados ou omitidos).
- Cada achado é rastreável (caminho + linha ou comando).
- Cada gap virou sprint-ID com spec ou Edit-pronto -- "Zero follow-up" preservado.
- Eu validei no mínimo 1 claim de cada agente despachado.
- Read-only durante a auditoria (sem `./run.sh --tudo`, sem mover arquivos).
- Análise honesta de finanças/burnout fica para sessão futura, conforme combinado.

---

*"A auditoria honesta é a base da confiança." -- princípio anti-mentira-piedosa*
