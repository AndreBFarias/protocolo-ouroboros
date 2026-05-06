# Sprints — Índice mestre

> Atualizado em 2026-05-05 (auditoria honesta do redesign + 14 sprints corretivas UX-RD-FIX).
> Antes em 2026-04-29 (brainstorming redesign). Mapeia todas as sprints do projeto: as **antigas em backlog** (pré-plan) versus o **plan ativo `pure-swinging-mitten`** (Ondas 1-6) versus o **plan lazy-noodling-wind** (UX-RD-* + roteiro corretivo UX-RD-FIX-*).
> Resolve conflitos (sprint antiga e nova endereçando o mesmo problema), absorções (antiga superseded por nova) e complementaridades (ortogonais).

## Status agregado

| Categoria | Quantidade |
|---|---|
| Concluídas em `docs/sprints/concluidos/` | ~130 |
| Backlog antigo (pré-plan) | 17 |
| Backlog novo (plan pure-swinging-mitten) | 61 |
| Arquivadas em `docs/sprints/arquivadas/` | 14 |
| **Total** | ~222 |

## Ondas do plan ativo (rota canônica)

Detalhe completo em `~/.claude/plans/pure-swinging-mitten.md`.

| Onda | Foco | Sprints | Status |
|---|---|---|---|
| **0** | **Blueprint + CI fix (pré-requisitos)** | **2 (DESIGN-01 + CI-01)** | **Backlog (P0)** |
| 1 | Anti-migué + restaurar débitos | 12 (ANTI-MIGUE-01..12) | **EM EXECUÇÃO** — 02, 03, 04, 07 concluídas em 2026-04-29 |
| 2 | ADR-08 LLM vivo + auditor cobertura (reescrito sob ADR-13) | 7 LLM-*-V2 (sub-spec AUDITOR-01 absorvida em LLM-04-V2) | Backlog (originais arquivadas via REVISAO-LLM-ONDA-01) |
| 3 | Cobertura documental universal | 20 (DOC-01..20) | Backlog |
| 4 | Cruzamento micro + IRPF + GAP proativo | 6 (MICRO-01..03 + IRPF-01..02 + GAP-01) | Backlog |
| 5 | Mobile bridge + fontes adicionais | 7 (MOB-01..03 + FONTE-01..04) | Backlog |
| 6 | UX/UI + OMEGA + pacote anual de vida | 16 (UX-01..09, UX-10 + OMEGA-94a..d + ADR-23 + MON-01 + DASH-01) -- **DEPRECADAS pelo plan lazy-noodling-wind** | Reabsorvido |

## Plan lazy-noodling-wind (redesign UX/UI 2026-05-04+) e roteiros sucessivos

Plan completo: `~/.claude/plans/lazy-noodling-wind.md`. Auditoria honesta: `docs/auditorias/AUDITORIA_REDESIGN_2026-05-05.md`.

| Fase | Sprints | Status |
|---|---|---|
| Onda 0-6 (UX-RD-01..19) | 19 sprints reescrevendo dashboard 1:1 com 29 mockups HTML | **CONCLUÍDAS** em 2026-05-04. Score real (auditoria): 64/100 |
| Fase Corretiva (UX-RD-FIX-01..14) | 14 sprints transversais corrigindo divergências catalogadas | **EXECUTADAS** em 2026-05-05 (gauntlet verde). Specs **arquivadas** em 2026-05-06 em `docs/sprints/arquivadas/2026-05-tentativa-fix-transversal/` porque a abordagem transversal não fechou a percepção visual integrada |
| **Fase Tela-a-Tela (UX-U-01..04 + UX-T-01..29 + UX-Q-01..03)** | 36 sprints em 3 ondas (U/T/Q) -- cada sprint entrega peça completa | **VIGENTE** -- ROTEIRO_TELAS_2026-05-06.md |

Plano operacional: `~/.claude/plans/auditoria-honesta-da-magical-lovelace.md`. Garantias: validação humana entre sprints, captura side-by-side mockup × dashboard automática, reversibilidade. Meta: score ≥95/100 após Q-03.

## Mapeamento das sprints antigas (17 em backlog pré-plan)

Para cada sprint antiga: qual é a relação com o plan novo, e qual o desfecho recomendado.

| Sprint antiga | Tema | Relação com plan novo | Desfecho |
|---|---|---|---|
| `sprint_24_automacao_bancaria` | Open Finance / Belvo | Ortogonal — pós-90d | **Manter em backlog.** Fora do escopo do plan, mas ainda válida. |
| `sprint_25_pacote_irpf` | Pacote IRPF completo | **Conflito** — superseded por `IRPF-01` (botão pacote IRPF) | **Absorver em IRPF-01.** Spec antiga vira referência histórica; conteúdo migrado para a nova. |
| `sprint_27b_grafo_motores_avancados` | Grafo motores avançados | Ortogonal | **Manter em backlog.** |
| `sprint_34_supervisor_auditor` | Supervisor LLM modo auditor | **Conflito** — superseded por `LLM-04` | **Absorver em LLM-04.** |
| `sprint_36_metricas_ia_dashboard` | Métricas autossuficiência | **Conflito** — superseded por `LLM-07` | **Absorver em LLM-07.** |
| `sprint_83_rename_protocolo_ouroboros` | Renomear projeto | Ortogonal | **Manter em backlog.** Decisão estratégica futura. |
| `sprint_84_schema_er_relacional_visual` | Visualização ER | Ortogonal | **Manter em backlog.** |
| `sprint_85_xlsx_docs_faltantes_expandido` | XLSX com docs faltantes | Complementar a `OMEGA-94*` | **Manter em backlog.** Pode ser absorvida quando OMEGA executar. |
| `sprint_86_ressalvas_humano_checklist` | Checklist humano | Ortogonal | **Manter em backlog.** |
| `sprint_93d_preservacao_forte_downloads` | Preservação de downloads | Ortogonal | **Manter em backlog.** |
| `sprint_93e_coluna_arquivo_origem_xlsx` | Coluna arquivo_origem no XLSX | Ortogonal | **Manter em backlog.** |
| `sprint_93h_limpeza_clones_andre` | Limpeza clones | Ortogonal — higiene operacional | **Manter em backlog.** |
| `sprint_94_fusao_total_vault_ouroboros` | Fusão total Vault | Ancestral de ADR-21 + Onda 5 (MOB-01/02) | **Absorvida** — manter em backlog como referência histórica. |
| `sprint_102_pagador_vs_beneficiario` | IRPF pagador vs beneficiário | Complementar a `IRPF-02` | **Manter em backlog.** Detalhe técnico que IRPF-02 vai consumir. |
| `sprint_AUDIT2_ENVELOPE_VS_PESSOA_CANONICO` | Path canônico envelope vs pessoa | **Conflito** — superseded por `ADR-23-DRAFT` | **Absorver em ADR-23-DRAFT.** |
| `sprint_Fa_ofx_duplicacao_accounts` | OFX dedup duplicação | Ortogonal — bug específico OFX | **Manter em backlog.** |
| `sprint_INFRA_PII_HISTORY` | PII history rewrite | Ortogonal | **Manter em backlog.** |

### Resumo do mapeamento

- **Conflitos resolvidos por absorção (4)**: Sprint 25 → IRPF-01; Sprint 34 → LLM-04; Sprint 36 → LLM-07; AUDIT2-ENVELOPE → ADR-23-DRAFT.
- **Ancestrais históricos (1)**: Sprint 94 já capturado em ADR-21 + MOB-01/02.
- **Mantidas em backlog (12)**: ortogonais ao plan, válidas como tarefas futuras independentes.

## Ação para sprints absorvidas

Para cada sprint absorvida, o conteúdo importante (gotchas, decisões, dependências) precisa ser **incorporado na spec nova** antes de fechar a antiga. Sprint nova fica como referência canônica; antiga ganha frontmatter `superseded_by: <ID novo>` e fica em backlog/ como histórico (não move para arquivadas/ porque o trabalho conceitual ainda vai ser feito, só com nome novo).

## Ordem de execução recomendada

1. **Onda 1 restante** (ANTI-MIGUE-01, 05, 06, 08, 09, 10, 11, 12) — bloqueia Ondas 2-6.
2. **Onda 2** (LLM-01..07) — habilita Ondas 3 e 6 (LLM-02 supervisor automatiza criação de extratores novos).
3. **Onda 3** (DOC-01..19) — depende de Onda 2 + ANTI-MIGUE-01 (gate 4-way).
4. **Onda 4** (MICRO + IRPF) — depende de DOC-02 + DOC-19.
5. **Onda 5** (MOB + FONTE) — independente; pode executar em paralelo a Onda 3 ou 4.
6. **Onda 6** (UX + OMEGA + MON) — fechamento; depende parcialmente das anteriores.
7. **Backlog antigo** — executado entre ondas conforme prioridade do dono.


## Tabela navegavel: 95 specs em backlog (atualizada 2026-04-29 após D7-extendida)

Ordenacao: P0 -> P1 -> P2 -> P3 -> ?? -> alfabetica. Para detalhes, abra a spec correspondente em `docs/sprints/backlog/<slug>.md`.

| Prio | Onda | Slug | Esforço | Depende de |
|------|------|------|---------|------------|
| P0 | 3 | `sprint_doc_13_multi_foto_selector` | 4h | nenhuma |
| P0 | 3 | `sprint_doc_16_danfe_validar_ingestao` | 1h | nenhuma |
| P0 | 4 | `sprint_link_audit_01_investigar_documentos_sem_aresta_documento_de` | 4h | nenhuma |
| P0 | 5 | `sprint_mob_01_vault_bridge_md` | 5h | nenhuma |
| P0 | 5 | `sprint_mob_02_mobile_cache_gen` | 4h | MOB-01 |
| P0 | 6 | `sprint_ux_01_callouts_dracula` | 2h | nenhuma |
| P1 | 2 | `sprint_agentic_fallback_01_extracao_para_tipos_sem_extrator` | 5h | VALIDAÇÃO-CSV-01 |
| P1 | 3 | `sprint_doc_01_amazon_pedido` | 5h | LLM-01, ANTI-MIGUE-01 |
| P1 | 3 | `sprint_doc_02_mercado_nf_fisica` | 5h | LLM-01, ANTI-MIGUE-01 |
| P1 | 3 | `sprint_doc_03_carteira_estudante` | 3h | LLM-01, ANTI-MIGUE-01 |
| P1 | 3 | `sprint_doc_04_cnh` | 3h | LLM-01, ANTI-MIGUE-01 |
| P1 | 3 | `sprint_doc_05_rg` | 3h | LLM-01, ANTI-MIGUE-01 |
| P1 | 3 | `sprint_doc_06_diploma` | 3h | LLM-01, ANTI-MIGUE-01 |
| P1 | 3 | `sprint_doc_07_historico_escolar` | 4h | LLM-01, ANTI-MIGUE-01 |
| P1 | 3 | `sprint_doc_08_certidao_nascimento` | 3h | LLM-01, ANTI-MIGUE-01 |
| P1 | 3 | `sprint_doc_09_exame_medico` | 5h | LLM-01, ANTI-MIGUE-01 |
| P1 | 3 | `sprint_doc_10_receita_medica_v2` | 3h | LLM-01, ANTI-MIGUE-01 |
| P1 | 3 | `sprint_doc_11_plano_saude_carteirinha` | 3h | LLM-01, ANTI-MIGUE-01 |
| P1 | 3 | `sprint_doc_12_govbr_pdf` | 4h | LLM-01, ANTI-MIGUE-01 |
| P1 | 3 | `sprint_doc_17_ocr_energia_cleanup` | 3h | nenhuma |
| P1 | 3 | `sprint_doc_18_holerite_detectar_novas_empresas` | 4h | LLM-02 |
| P1 | 3 | `sprint_doc_20_extrato_investimento_corretora` | 5h | LLM-01, ANTI-MIGUE-01 |
| P1 | 3 | `sprint_ocr_audit_01_validar_qualidade_ocr_amostras` | 5h | ANTI-MIGUE-01 |
| P1 | 3 | `sprint_test_audit_01_expandir_fixtures_reais_para_30_amostras` | 8h | nenhuma |
| P1 | 4 | `sprint_gap_01_alerta_proativo_transacao_sem_nf` | 4h | MICRO-01 |
| P1 | 4 | `sprint_irpf_01_pacote_irpf_botao` | 5h | MICRO-01 |
| P1 | 4 | `sprint_micro_01_linking_micro_runtime` | 5h | DOC-02, DOC-19 |
| P1 | 5 | `sprint_fonte_01_google_calendar_ics` | 4h | nenhuma |
| P1 | 5 | `sprint_fonte_02_thunderbird_email_local` | 5h | nenhuma |
| P1 | 5 | `sprint_fonte_04_assinaturas_detector` | 3h | nenhuma |
| P1 | 6 | `sprint_mon_01_vault_obsidian_dessincronia` | 3h | nenhuma |
| P1 | 6 | `sprint_ux_02_treemap_heatmap_wcag` | 3h | nenhuma |
| P2 | 1 | `sprint_fix_test_busca_indice_fragil` | 1.5h | nenhuma |
| P2 | 1 | `sprint_hook_inbox_01_aviso_arquivos_pendentes` | 1h | nenhuma |
| P2 | 2 | `sprint_llm_03_v2_proposicao_regra_categoria` | 1h | LLM-01-V2 |
| P2 | 2 | `sprint_llm_05_v2_revisor_tab_proposicoes` | 3h | LLM-01-V2, LLM-03-V2 |
| P2 | 2 | `sprint_validar_batch_01_skill_validar_inbox` | 2h | VALIDAÇÃO-CSV-01 |
| P2 | 3 | `sprint_doc_14_anti_duplicacao_semantica` | 3h | nenhuma |
| P2 | 3 | `sprint_doc_15_parse_data_br_centralizado` | 4h | nenhuma |
| P2 | 4 | `sprint_grafo_xlsx_01_investigar_discrepancia_xlsx_grafo` | 2h | nenhuma |
| P2 | 4 | `sprint_irpf_02_irpf_dedutivel_medico` | 3h | DOC-09, DOC-10 |
| P2 | 4 | `sprint_micro_02_items_canonicos_yaml` | 3h | MICRO-01 |
| P2 | 4 | `sprint_micro_03_aba_cruzamento_micro` | 4h | MICRO-01, MICRO-02 |
| P2 | 5 | `sprint_fonte_03_thunderbird_ics_local` | 3h | FONTE-01 |
| P2 | 5 | `sprint_mob_03_pessoa_a_b_refactor` | 4h | nenhuma |
| P2 | 6 | `sprint_dash_01_pacote_anual_de_vida` | 4h | IRPF-01, OMEGA-94a, OMEGA-94b, OMEGA-... |
| P2 | 6 | `sprint_omega_94a_aba_saude` | 5h | DOC-09, DOC-10, DOC-11 |
| P2 | 6 | `sprint_omega_94b_aba_identidade` | 4h | DOC-04, DOC-05 |
| P2 | 6 | `sprint_omega_94c_aba_profissional` | 3h | nenhuma |
| P2 | 6 | `sprint_omega_94d_aba_academica` | 3h | DOC-06, DOC-07 |
| P2 | 6 | `sprint_ux_03_drilldown_em_5_plots` | 5h | nenhuma |
| P2 | 6 | `sprint_ux_04_revisor_responsivo_50_itens` | 3h | nenhuma |
| P2 | 6 | `sprint_ux_10_clarificar_cluster_vs_aba_nomenclatura` | 2h | nenhuma |
| P3 | 2 | `sprint_llm_06_v2_sha_guard_propostas_rejeitadas` | 1h | LLM-05-V2 |
| P3 | 2 | `sprint_llm_07_v2_metricas_autossuficiencia` | 2h | LLM-01-V2 |
| P3 | 3 | `sprint_doc_19_holerite_contem_item_sem_codigo` | 1h | nenhuma |
| P3 | 3 | `sprint_doc_21_extrator_contrato_locacao` | 4h | ANTI-MIGUE-01 (gate 4-way obrigatório... |
| P3 | 3 | `sprint_doc_22_extrator_iptu` | 3h | ANTI-MIGUE-01 |
| P3 | 3 | `sprint_doc_23_extrator_condominio` | 3h | ANTI-MIGUE-01 + Sprint 87.3 (extrator... |
| P3 | 3 | `sprint_doc_24_extrator_crlv_crv` | 4h | ANTI-MIGUE-01 |
| P3 | 3 | `sprint_doc_25_extrator_ipva_seguro_auto` | 4h | DOC-24 (precisa node veículo no grafo) |
| P3 | 3 | `sprint_doc_26_extrator_multas_detran` | 3h | DOC-24 |
| P3 | 6 | `sprint_adr_23_draft_adr_23_envelope_vs_pessoa_canonico` | 1h (decisão) + variável (execução) | nenhuma |
| P3 | 6 | `sprint_dash_02_yaml_contatos_emergencia` | 2h | nenhuma |
| P3 | 6 | `sprint_dash_03_yaml_beneficiarios` | 2h | DASH-02 (mesmo padrão estrutural) |
| P3 | 6 | `sprint_ux_05_pyvis_fallback_decente` | 1h | nenhuma |
| P3 | 6 | `sprint_ux_06_doc_coluna_observabilidade` | 1h | nenhuma |
| P3 | 6 | `sprint_ux_07_snapshot_timestamp_dinamico` | 1h | nenhuma |
| P3 | 6 | `sprint_ux_08_deep_link_test_completo` | 2h | nenhuma |
| P3 | 6 | `sprint_ux_09_cleanup_docstrings_quebradas` | 30min | nenhuma |
| P3 | frozen | `sprint_subagente_extracao_01_paralelizacao_FROZEN` | 10h | AGENTIC-FALLBACK-01, VALIDAR-BATCH-01, volume |
| P3 | ? | `sprint_AUDIT2_ENVELOPE_VS_PESSOA_CANONICO` | ? | ? |
| ?? | ? | `sprint_102_pagador_vs_beneficiario` | ? | ? |
| ?? | ? | `sprint_24_automacao_bancaria` | ? | ? |
| ?? | ? | `sprint_25_pacote_irpf` | ? | ? |
| ?? | ? | `sprint_27b_grafo_motores_avancados` | ? | ? |
| ?? | ? | `sprint_83_rename_protocolo_ouroboros` | ? | ? |
| ?? | ? | `sprint_84_schema_er_relacional_visual` | ? | ? |
| ?? | ? | `sprint_85_xlsx_docs_faltantes_expandido` | ? | ? |
| ?? | ? | `sprint_86_ressalvas_humano_checklist` | ? | ? |
| ?? | ? | `sprint_93d_preservacao_forte_downloads` | ? | ? |
| ?? | ? | `sprint_93e_coluna_arquivo_origem_xlsx` | ? | ? |
| ?? | ? | `sprint_93h_limpeza_clones_andre` | ? | ? |
| ?? | ? | `sprint_94_fusao_total_vault_ouroboros` | ? | ? |
| ?? | ? | `sprint_Fa_ofx_duplicacao_accounts` | ? | ? |
| ?? | ? | `sprint_INFRA_PII_HISTORY` | ? | ? |

> Tabela gerada automaticamente lendo frontmatter de cada spec. Quando criar spec nova, declare `**Prioridade**: P[0-3]`, `**Onda**: <numero>`, `**Esforço estimado**: <duracao>`, `**Depende de**: <slug ou nenhuma>` para entrar aqui ordenada.

---

## Princípio de manutenção

Este índice deve ser atualizado:
- Quando uma sprint do plan **muda de fase** (backlog → em-progresso → concluída).
- Quando uma sprint antiga é **absorvida ou arquivada**.
- Quando uma sprint nova é criada como **achado colateral**.

A meta é: zero sprint silenciosa, zero conflito não-mapeado, zero TODO solto.

---

*"Saber onde cada peça encaixa é metade do trabalho de organizar." — princípio do índice canônico*
