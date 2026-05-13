---
titulo: Roadmap canonico ate "prod ready" -- 8 epicos ordenados
data: 2026-05-13
autor: supervisor Opus principal
escopo: organiza 119 specs em backlog/ + as recem-criadas em uma ordem integrada
referencia: contexto/POR_QUE.md secao "Ciclo de graduacao Opus -> ETL"
---

# ROADMAP ate prod -- 8 epicos canonicos

## Filosofia (presumida em toda spec nova)

O projeto so chega em "prod" (`./run.sh --full-cycle` roda autonomo, dono so joga arquivos na inbox e confia) quando:

1. **Cada tipo documental que entra na inbox esta GRADUADO** -- >=2 amostras 4-way verdes (Opus multimodal × ETL × Grafo × Humano). Ver `contexto/POR_QUE.md`.
2. **Robustez operacional minima** -- backup automatico, transacionalidade, lockfile, retencao.
3. **Cobertura de linking** documento->transacao acima de 30% (hoje 0.41%).  <!-- noqa: accent -->
4. **Categorizacao** com `Outros` abaixo de 5% das transacoes (hoje 17.7%).  <!-- noqa: accent -->
5. **Dashboard utilizavel** pelo casal sem leitura de docs internos.

## Regra de prioridade

- **P0** = bloqueia prod (sem isso, ETL nao pode rodar sozinho com confianca).  <!-- noqa: accent -->
- **P1** = degrada UX diaria (uso funciona, mas tem atrito recorrente).
- **P2** = ampliacao da utilidade (mais tipos, mais fontes).
- **P3** = saneamento (debito tecnico sem efeito direto no usuario).

Cada epico tem **critério de pronto** mensurável. Sub-sprints existem **dentro** de épicos -- nada fica solto.

---

## EPICO 1 -- Fase A: Graduar todos os tipos documentais (P0)

**Critério de pronto**: `data/output/graduacao_tipos.json` mostra >=15 tipos GRADUADOS. Dashboard `graduacao_tipos.py` exibe tabela viva.

**Mãe**: `FASE-A-COMPLETAR-VALIDACAO-ARTESANAL` (novo 2026-05-13).

### Sub-sprints prioritárias (graduar tipos com amostras já no grafo)

| ID | Status atual | Esforço | Meta |
|---|---|---|---|
| INFRA-VALIDACAO-ARTESANAL-CUPOM | GRADUADO 2026-05-12 | -- | confirmar |
| INFRA-VALIDACAO-ARTESANAL-HOLERITE | GRADUADO 2026-05-12 | -- | confirmar |
| INFRA-VALIDACAO-ARTESANAL-DAS | GRADUADO 2026-05-12 | -- | confirmar |
| INFRA-VALIDACAO-ARTESANAL-NFCE | GRADUADO 2026-05-12 | -- | confirmar |
| INFRA-SUBSTITUIR-CACHE-SINTETICO-CUPOM | parcial | 2h | fechar |
| FASE-A-VALIDAR-PIX (criar) | CALIBRANDO (3 caches) | 2h | graduar PIX |
| FASE-A-VALIDAR-BOLETO-SERVICO (criar) | PENDENTE | 3h | 2 amostras |
| FASE-A-VALIDAR-DIRPF (criar) | PENDENTE | 3h | 2 amostras |

### Sub-sprints de extrator novo (tipos sem extrator ainda)

| ID existente | Tipo entregue |
|---|---|
| doc_09_exame_medico | exame_medico |
| doc_10_receita_medica_v2 | receita_medica |
| doc_16_danfe_validar_ingestao | danfe (validar) |
| doc_17_ocr_energia_cleanup | conta_energia |
| doc_18_holerite_detectar_novas_empresas | holerite (escalar) |
| doc_19_holerite_contem_item_sem_codigo | holerite (corner case) |
| doc_22_extrator_iptu | conta_iptu |
| doc_23_extrator_condominio | condominio |
| doc_24_extrator_crlv_crv | crlv |
| doc_25_extrator_ipva_seguro_auto | ipva, seguro_auto |
| doc_26_extrator_multas_detran | multa_detran |
| doc_20_extrato_investimento_corretora | extrato_corretora |
| doc_21_extrator_contrato_locacao | contrato |
| doc_28_passaporte | passaporte |
| doc_01_amazon_pedido | pedido_amazon |
| doc_02_mercado_nf_fisica | nf_mercado |
| doc_03_carteira_estudante | id_estudante |
| doc_04_cnh / doc_05_rg / doc_06_diploma / doc_07_historico_escolar / doc_08_certidao_nascimento / doc_11_plano_saude_carteirinha / doc_12_govbr_pdf | docs identidade/academicos |
| doc_13_multi_foto_selector | infra OCR |
| doc_14_anti_duplicacao_semantica | infra qualidade |
| doc_15_parse_data_br_centralizado | infra parsing |
| agentic_fallback_01_extracao_para_tipos_sem_extrator | fallback geral |

**Esforço épico**: 60-80h ao longo de 4-6 semanas. Dono fornece amostras conforme aparecem na vida real.

---

## EPICO 2 -- Robustez operacional para uso diário (P0)

**Critério de pronto**: `./run.sh --tudo` pode crashar em qualquer estágio sem perda de dados. Backup automático pré-pipeline. Lockfile impede 2 instâncias simultâneas. Logs rotacionam.

| ID | Esforço | Bloqueia |
|---|---|---|
| INFRA-BACKUP-GRAFO-AUTOMATIZADO (novo) | 2h | -- |
| INFRA-PIPELINE-TRANSACIONALIDADE (novo) | 4h | INFRA-BACKUP-GRAFO-AUTOMATIZADO |
| INFRA-PII-HISTORY (existente) | 3h | -- |
| INFRA-INTEGRAR-AUDIT-VAULT-CHECK | 1h | -- |
| propor_extrator_idempotencia_timestamp | 2h | -- |
| fix_micro_01_path_canonico | 1h | -- |

**Esforço épico**: 13h ao longo de 1 semana.

---

## EPICO 3 -- Qualidade dos dados: linking + categorização (P1)

**Critério de pronto**: linking documento_de >= 30% (hoje 0.41%). `Outros` na categorização <= 5% (hoje 17.7%). Dashboard mostra cobertura viva.

### Sub-sprints

| ID | Foco |
|---|---|
| link_audit_01_investigar_documentos_sem_aresta_documento_de | medir cobertura real |
| link_tuning_01_ajustar_linking_config | tolerâncias por tipo |
| INFRA-LINKING-HOLERITE-TOLERANCIA-RECALIBRAR | 5% → 20% G4F+INFOBASE |
| gap_01_alerta_proativo_transacao_sem_nf | UX feedback |
| grafo_xlsx_01_investigar_discrepancia_xlsx_grafo | sanidade |
| 93d_preservacao_forte_downloads | qualidade fonte |
| 93e_coluna_arquivo_origem_xlsx | rastreabilidade |
| 93h_limpeza_clones_andre | dedup retroativo |
| ocr_audit_01_validar_qualidade_ocr_amostras | OCR baseline |
| micro_01_linking_micro_runtime | micro-linking |
| micro_01a_followup_nfce_reais | NFCe reais |
| micro_01b_linking_mercado_holerite | cruzar mercado-holerite |
| micro_02_items_canonicos_yaml | itens canônicos |
| micro_03_aba_cruzamento_micro | aba dashboard |

**Esforço épico**: 30-40h ao longo de 2-3 semanas.

---

## EPICO 4 -- IRPF e operações financeiras (P1)

**Critério de pronto**: dashboard tem "Pacote IRPF" 1-click com PDF anual + memorial de cálculo. Pagador vs beneficiário modelado.

| ID | Foco |
|---|---|
| 25_pacote_irpf | pacote anual |
| irpf_01_pacote_irpf_botao | UX 1-click |
| irpf_02_irpf_dedutivel_medico | regra dedução médica |
| 102_pagador_vs_beneficiario | quem paga vs quem usa |
| 24_automacao_bancaria | scraping legal |

**Esforço épico**: 20-25h.

---

## EPICO 5 -- UX dashboard pronto para casal (P1)

**Critério de pronto**: Vitória consegue usar o dashboard sem ajuda. 4 clusters (Hoje/Dinheiro/Saúde/Documentos) limpos. Mobile pix aparece.

| ID |
|---|
| MOB-dashboard-mostra-pix-app |
| dash_01_pacote_anual_de_vida |
| dash_02_yaml_contatos_emergencia |
| dash_03_yaml_beneficiarios |
| ux_01_callouts_dracula |
| ux_02_treemap_heatmap_wcag |
| ux_03_drilldown_em_5_plots |
| ux_04_revisor_responsivo_50_itens |
| ux_05_pyvis_fallback_decente |
| ux_06_doc_coluna_observabilidade |
| ux_07_snapshot_timestamp_dinamico |
| ux_08_deep_link_test_completo |
| UX-AUDIT-VISUAL-2026-05-12 |
| UX-INFRA-SPLIT-RESTANTES |
| ROTEIRO_TELAS_2026-05-06 |
| 27b_grafo_motores_avancados |
| 84_schema_er_relacional_visual |
| 85_xlsx_docs_faltantes_expandido |
| 86_ressalvas_humano_checklist |

**Esforço épico**: 35-45h.

---

## EPICO 6 -- Mobile bridge (Protocolo-Mob-Ouroboros) (P2)

**Critério de pronto**: foto tirada no app aparece classificada no dashboard em <5min. Camera bug fixado. Áudio transcrito.

| ID |
|---|
| MOB-bug-camera-momento-repro |
| MOB-spec-transcricao-audio |
| mob_01_vault_bridge_md |
| mob_02_mobile_cache_gen |
| mob_03_pessoa_a_b_refactor |
| mon_01_vault_obsidian_dessincronia |
| hook_inbox_01_aviso_arquivos_pendentes |
| 94_fusao_total_vault_ouroboros |

**Esforço épico**: 20-30h.

---

## EPICO 7 -- Inteligência aumentada (LLM revisor + fontes externas + omega) (P2-P3)

**Critério de pronto**: revisor LLM v2 propõe regras de categoria automaticamente. Calendar/Thunderbird ingeridos.

| ID |
|---|
| omega_94a_aba_saude / 94b_identidade / 94c_profissional / 94d_academica |
| llm_03_v2_proposicao_regra_categoria |
| llm_05_v2_revisor_tab_proposicoes |
| llm_06_v2_sha_guard_propostas_rejeitadas |
| llm_07_v2_metricas_autossuficiencia |
| fonte_01_google_calendar_ics |
| fonte_02_thunderbird_email_local |
| fonte_03_thunderbird_ics_local |
| fonte_04_assinaturas_detector |
| subagente_extracao_01_paralelizacao_FROZEN |

**Esforço épico**: 40-50h.

---

## EPICO 8 -- Saneamento técnico contínuo (P3)

**Critério de pronto**: pylint/lint zero. Acentuação 100%. Testes >=3000. Docstrings limpas.

| ID |
|---|
| INFRA-LINT-ACENTUACAO-SPECS-2026-05-12 |
| lint_acentuacao_divida_pre_existente |
| ux_09_cleanup_docstrings_quebradas |
| ux_10_clarificar_cluster_vs_aba_nomenclatura |
| meta_codigo_relacionado_01_template_spec |
| meta_dep_linter_01_validar_dependencias_backlog |
| retrabalho_extratores_01_auditoria_d7 |
| test_audit_01_expandir_fixtures_reais_para_30_amostras |
| fix_test_busca_indice_fragil |
| validar_batch_01_skill_validar_inbox |
| AUDIT2_ENVELOPE_VS_PESSOA_CANONICO |
| adr_23_draft_adr_23_envelope_vs_pessoa_canonico |
| Fa_ofx_duplicacao_accounts |
| 83_rename_protocolo_ouroboros |
| INFRA-split-* (5 sprints arquivadas pela revogação da regra h) |

**Esforço épico**: 20-30h (rola em paralelo com outros).

---

## Ordem de execução recomendada

```
T+0          : Iniciar EPICO 1 (Fase A) + EPICO 2 (operacional) em paralelo.
                EPICO 1 depende de amostras reais; EPICO 2 é puro código.
T+2 semanas  : EPICO 1 com >=10 tipos GRADUADOS. EPICO 2 fechado.
                Iniciar EPICO 3 (qualidade dados).
T+4 semanas  : EPICO 1 com 15+ tipos GRADUADOS. EPICO 3 fechado.
                Iniciar EPICO 4 (IRPF) + EPICO 5 (UX) em paralelo.
T+6 semanas  : EPICO 4 fechado (pacote IRPF 1-click).
                EPICO 5 com fluxos principais limpos.
                ===> PROD CANDIDATA <===
T+8 semanas  : EPICO 6 (mobile) + EPICO 8 (saneamento) em paralelo.
T+12 semanas : EPICO 7 (inteligência aumentada) opcional.
```

## Anti-débito: como evitar sprints separadas e perdidas

1. **Todo achado colateral** durante execução vira sub-sprint DENTRO de um épico, nunca fora.
2. **Cada commit que muda este roadmap** atualiza a coluna Status do épico correspondente.
3. **Sprint que não cabe em épico** = sinal de que falta um épico. Não criar spec sem revisar este arquivo primeiro.
4. **Sub-sprints listadas aqui** mas sem spec própria em `backlog/` ganham spec quando entram em execução.

## Métricas globais de prontidão

| Métrica | Hoje (2026-05-13) | Meta prod |
|---|---|---|
| Tipos GRADUADOS | 4 | 15+ |
| Linking `documento_de` | 0.41% (25/6086) | >=30% |
| Categorização "Outros" | 17.7% (1031/5840) | <=5% |
| Pytest passed | 2964 | >=3000 |
| Backup grafo automático | Não | Sim |
| Transacionalidade pipeline | Não | Sim |
| Lockfile concorrência | Não | Sim |
| Páginas dashboard produtivas | ~30/39 | 100% |

---

*"Roadmap nao e profecia, e bússola. Sub-sprints sao passos; epicos sao chegadas." -- principio do mapa vivo*  <!-- noqa: accent -->
