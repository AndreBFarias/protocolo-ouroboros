---
titulo: Roadmap canonico ate "prod ready" -- 8 epicos ordenados
data: 2026-05-13
autor: supervisor Opus principal
escopo: organiza todas as specs em backlog/ em 8 epicos com entregavel concreto
referencia:
  - docs/CICLO_GRADUACAO_OPERACIONAL.md (ritual obrigatorio antes de cada sprint)  <!-- noqa: accent -->
  - scripts/dossie_tipo.py (CLI de auditoria por tipo documental)
  - data/output/graduacao_tipos.json (estado vivo dos tipos)
---

# ROADMAP ate prod -- 8 epicos canonicos

## Filosofia (presumida em toda spec nova)

O projeto chega em "prod" quando: dono joga arquivo em `inbox/`, roda `./run.sh --full-cycle`, e tudo aparece corretamente catalogado/categorizado/linkado SEM revisao humana.

Para chegar la, cada **tipo documental** percorre o ciclo de graduacao:

1. **PENDENTE** -- nenhuma amostra real validada artesanalmente.
2. **CALIBRANDO** -- 1 amostra validada (Opus multimodal le, gera "prova dos 7" artesanal, ETL roda contra mesma amostra, supervisor confirma 4-way: Opus × ETL × Grafo × Humano).
3. **GRADUADO** -- >=2 amostras 4-way verdes consecutivas. ETL processa o tipo autonomamente.
4. **REGREDINDO** -- ja graduado, mas amostra recente divergiu (alerta de re-calibracao).

### Ritual obrigatorio antes de cada sprint que toca um tipo documental  <!-- noqa: accent -->

**O Opus principal SEMPRE coordena como humano artesao.** Sequencia inegociavel para sprint de tipo `X`:

1. `scripts/dossie_tipo.py --abrir X` -- ve estado atual do dossie do tipo.
2. Se nao ha amostra recente: dono fornece via inbox; supervisor seleciona.  <!-- noqa: accent -->
3. **PROVA ARTESANAL ANTES**: Opus le a amostra via Read multimodal e gera `prova_artesanal_<sha256>.json` no dossie. So entao decide o que pedir ao executor.
4. `scripts/dossie_tipo.py --comparar X <sha256>` apos o ETL rodar -- compara prova vs output do ETL automaticamente.
5. Se concordam: amostra GRADUADA, contador +1. Se ja eram 2 amostras verdes: tipo passa a GRADUADO.
6. Se divergem: relatorio em `divergencias_<sha256>.md`, executor re-disparado com brief de correcao.  <!-- noqa: accent -->

**A consequencia operacional**: cada sprint encerra com **produto final entregue** -- nao ha "sprints intermediarias de fechamento". Quem fechar a sprint encerra com o dossie do tipo atualizado e (idealmente) com graduacao avancando.  <!-- noqa: accent -->

## Metricas globais de prontidao (atualizadas continuamente)

<!-- BEGIN_AUTO_METRICAS_PRONTIDAO -->
| Métrica | Hoje | Meta prod |
|---|---|---|
| Tipos GRADUADOS | 9 | >=16 |
| Linking `documento_de` | 0.46% (28/6086) | >=30% |
| Categorização Outros | 17.7% (1031/5840) | <=5% |
| Backup grafo automático | Sim | Sim |
| Transacionalidade pipeline | Sim | Sim |
| Lockfile concorrência | Não | Sim |
| Páginas dashboard | 39 | 40+ |
| Pytest passed | 3099 | (estável, sem regressão) |
<!-- END_AUTO_METRICAS_PRONTIDAO -->


| Métrica | Hoje (2026-05-13) | Meta prod |
|---|---|---|
| Tipos GRADUADOS | 4 (cupom, holerite, das, nfce) | >=15 |
| Linking `documento_de` | 0.41% (25/6086) | >=30% |
| Categorizacao "Outros" | 17.7% (1031/5840) | <=5% |
| Backup grafo automatico | Nao | Sim |
| Transacionalidade pipeline | Nao | Sim |
| Lockfile concorrencia | Nao | Sim |
| Paginas dashboard produtivas | ~30/39 | 100% |
| Pytest passed | 2964 | (estavel, sem regressao) |

## Regra de prioridade

- **P0** = bloqueia prod (sem isso, ETL nao pode rodar autonomo).  <!-- noqa: accent -->
- **P1** = degrada UX diaria (uso funciona, mas tem atrito).
- **P2** = ampliacao da utilidade (mais tipos, mais fontes).
- **P3** = saneamento (debito tecnico sem efeito direto no usuario).

## Anti-fragmentacao

- Toda spec NOVA pertence a um epico aqui mapeado. Se nao cabe, ou voce esta inventando trabalho fora de ordem, ou falta um epico (criar epico antes da spec).  <!-- noqa: accent -->
- Achado colateral durante execucao vira sub-sprint DENTRO de epico, nunca avulsa.  <!-- noqa: accent -->
- Sub-sprint nao listada aqui que aparece no backlog/: re-mapear para epico apropriado no proximo commit ao roadmap.  <!-- noqa: accent -->

---

## EPICO 1 -- Fase A: Graduar todos os tipos documentais (P0)

**Entregavel**: `data/output/graduacao_tipos.json` mostra >=15 tipos GRADUADOS. Dashboard `graduacao_tipos.py` exibe tabela viva. Cada tipo tem dossie populado em `data/output/dossies/<tipo>/`.

**Mae**: `FASE-A-COMPLETAR-VALIDACAO-ARTESANAL` (2026-05-13).

### Sub-sprints prioritarias (graduar tipos com amostras ja no grafo)

| ID | Status atual | Entregavel da sub-sprint |
|---|---|---|
| INFRA-VALIDACAO-ARTESANAL-CUPOM | GRADUADO 2026-05-12 | confirmar dossie + json |
| INFRA-VALIDACAO-ARTESANAL-HOLERITE | GRADUADO 2026-05-12 | confirmar dossie + json |
| INFRA-VALIDACAO-ARTESANAL-DAS | GRADUADO 2026-05-12 | confirmar dossie + json |
| INFRA-VALIDACAO-ARTESANAL-NFCE | GRADUADO 2026-05-12 | confirmar dossie + json |
| INFRA-SUBSTITUIR-CACHE-SINTETICO-CUPOM | parcial | fechar substituicao |
| FASE-A-VALIDAR-PIX (criar) | CALIBRANDO (3 caches reais Itau/C6/Nubank) | graduar PIX |
| FASE-A-VALIDAR-BOLETO-SERVICO (criar) | PENDENTE | 2 amostras validadas |
| FASE-A-VALIDAR-DIRPF (criar) | PENDENTE | 2 amostras validadas |

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

---

## EPICO 2 -- Robustez operacional para uso diario (P0)

**Entregavel**: `./run.sh --tudo` pode crashar em qualquer estagio sem perda de dados. Backup automatico antes do pipeline. Lockfile impede 2 instancias. Logs rotacionam. `--restore-grafo <ts>` funcional.

| ID | Entregavel |
|---|---|
| INFRA-BACKUP-GRAFO-AUTOMATIZADO (2026-05-13) | snapshot + retencao 7d + restore CLI |
| INFRA-PIPELINE-TRANSACIONALIDADE (2026-05-13) | BEGIN/COMMIT por estagio + rollback granular |
| INFRA-PII-HISTORY | scrub retroativo de PII em logs |
| INFRA-INTEGRAR-AUDIT-VAULT-CHECK | audit roda em `./run.sh --check` |
| propor_extrator_idempotencia_timestamp | idempotencia provada |
| fix_micro_01_path_canonico | paths canonicos no grafo |

---

## EPICO 3 -- Qualidade dos dados: linking + categorizacao (P1)

**Entregavel**: linking `documento_de` >= 30%. `Outros` na categorizacao <= 5%. Dashboard mostra cobertura viva.

| ID | Foco |
|---|---|
| link_audit_01_investigar_documentos_sem_aresta_documento_de | medir cobertura real |
| link_tuning_01_ajustar_linking_config | tolerancias por tipo |
| INFRA-LINKING-HOLERITE-TOLERANCIA-RECALIBRAR | 5% -> 20% G4F+INFOBASE |
| gap_01_alerta_proativo_transacao_sem_nf | UX feedback |
| grafo_xlsx_01_investigar_discrepancia_xlsx_grafo | sanidade |
| 93d_preservacao_forte_downloads | qualidade fonte |
| 93e_coluna_arquivo_origem_xlsx | rastreabilidade |
| 93h_limpeza_clones_andre | dedup retroativo |
| ocr_audit_01_validar_qualidade_ocr_amostras | OCR baseline |
| micro_01_linking_micro_runtime | micro-linking |
| micro_01a_followup_nfce_reais | NFCe reais |
| micro_01b_linking_mercado_holerite | cruzar mercado-holerite |
| micro_02_items_canonicos_yaml | itens canonicos |
| micro_03_aba_cruzamento_micro | aba dashboard |

---

## EPICO 4 -- IRPF e operacoes financeiras (P1)  <!-- noqa: accent -->

**Entregavel**: dashboard tem "Pacote IRPF" 1-click com PDF anual + memorial. Pagador vs beneficiario modelado.

| ID | Foco |
|---|---|
| 25_pacote_irpf | pacote anual |
| irpf_01_pacote_irpf_botao | UX 1-click |
| irpf_02_irpf_dedutivel_medico | regra deducao medica |
| 102_pagador_vs_beneficiario | quem paga vs quem usa |
| 24_automacao_bancaria | scraping legal |

---

## EPICO 5 -- UX dashboard pronto para casal (P1)

**Entregavel**: Vitoria usa o dashboard sem ajuda. 4 clusters limpos. Mobile pix aparece.

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
| UX-DASH-GRADUACAO-TIPOS (criar) | tabela viva dos tipos |

---

## EPICO 6 -- Mobile bridge (Protocolo-Mob-Ouroboros) (P2)

**Entregavel**: foto tirada no app aparece classificada no dashboard em <5min. Camera bug fixado. Audio transcrito.

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

---

## EPICO 7 -- Inteligencia aumentada (LLM revisor v2 + fontes + omega) (P2-P3)

**Entregavel**: revisor LLM v2 propoe regras de categoria automaticamente. Calendar/Thunderbird ingeridos. Omega 4 abas vivas.

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

---

## EPICO 8 -- Saneamento tecnico continuo (P3)

**Entregavel**: lint zero. Acentuacao 100%. Testes estaveis. Docstrings limpas. Nenhuma sprint avulsa fora de epico.

| ID |
|---|
### Sub-grupo 8a: Onboarding e discoverability (P0/P1) -- nascidas em 2026-05-13

| ID | Prioridade | Foco |
|---|---|---|
| META-ONBOARDING-NOVA-SESSAO | P0 | CLAUDE.md no root + README com filosofia |
| META-VALIDATOR-BRIEF-TRACKEADO | P0 | padroes (a..ll) para docs/PADROES_CANONICOS.md (trackeado) |
| META-SUPERVISOR-OPUS-ATUALIZAR | P0 | docs/SUPERVISOR_OPUS.md cita ROADMAP + CICLO + dossie_tipo |
| META-TEMPLATE-FRONTMATTER-SPECS | P1 | template + scripts/normalizar_specs.py para 97 specs |
| META-HOOK-SESSION-START-PROJETO | P1 | hook local injeta estado vivo no contexto inicial |
| META-PROMPT-NOVA-SESSAO-TRACKEADO | P1 | docs/PROMPT_NOVA_SESSAO.md sem PII |

### Sub-grupo 8b: Debito tecnico historico

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
| INFRA-split-* (5 sprints arquivadas pela revogacao da regra h) |

---

## Cadeia de execucao recomendada  <!-- noqa: accent -->

```
Onda 1 (paralela)      : Epicos 1 + 2 -- comecar imediatamente.
                         Epico 1 depende de amostras reais que dono fornece.
                         Epico 2 e puro codigo (sem dependencia humana).

Onda 2 (apos onda 1)   : Epico 3 -- requer pipeline robusto + tipos graduados.

Onda 3 (apos onda 2)   : Epicos 4 + 5 paralelos.

===> PROD CANDIDATA <===  apos Epicos 1+2+3+4+5 fechados.

Onda 4 (opcional)      : Epicos 6 + 7 + 8 ampliam utilidade pos-prod.
```

## Como uma sprint do roadmap "fecha" (sem sprint intermediaria)

Cada sprint do Epico 1 (graduacao de tipo) entrega produto final na primeira passagem:

1. Spec executada -> codigo + testes.  <!-- noqa: accent -->
2. Pipeline rodado contra >=2 amostras reais.
3. `scripts/dossie_tipo.py --comparar` produz veredito automatico.
4. Se graduado: `graduacao_tipos.json` atualizado, dashboard mostra a mudanca, spec movida para `concluidos/`.
5. Se divergente: gera `divergencias.md` E ja registra a sprint-filha de correcao no proprio epico (anti-debito automatico).

Sprints dos Epicos 2-8 fecham por entregavel canonico declarado no header do epico. Sem entregavel = nao fecha.  <!-- noqa: accent -->

---

*"Roadmap nao e profecia, e bussola. Sub-sprints sao passos; epicos sao chegadas." -- principio do mapa vivo*  <!-- noqa: accent -->
