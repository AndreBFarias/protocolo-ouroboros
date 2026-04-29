# Sprints — Índice mestre

> Atualizado em 2026-04-29 após brainstorming de redesign + auditoria honesta.
> Mapeia todas as sprints do projeto: as **antigas em backlog** (pré-plan) versus o **plan ativo `pure-swinging-mitten`** (Ondas 1-6).
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
| 1 | Anti-migué + restaurar débitos | 12 (ANTI-MIGUE-01..12) | **EM EXECUÇÃO** — 02, 03, 04, 07 concluídas em 2026-04-29 |
| 2 | ADR-08 LLM vivo | 7 (LLM-01..07) | Backlog |
| 3 | Cobertura documental universal | 19 (DOC-01..19) | Backlog |
| 4 | Cruzamento micro + IRPF | 5 (MICRO-01..03 + IRPF-01..02) | Backlog |
| 5 | Mobile bridge + fontes adicionais | 7 (MOB-01..03 + FONTE-01..04) | Backlog |
| 6 | UX/UI + OMEGA | 14 (UX-01..09 + OMEGA-94a..d + ADR-23 + MON-01) | Backlog |

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

## Princípio de manutenção

Este índice deve ser atualizado:
- Quando uma sprint do plan **muda de fase** (backlog → em-progresso → concluída).
- Quando uma sprint antiga é **absorvida ou arquivada**.
- Quando uma sprint nova é criada como **achado colateral**.

A meta é: zero sprint silenciosa, zero conflito não-mapeado, zero TODO solto.

---

*"Saber onde cada peça encaixa é metade do trabalho de organizar." — princípio do índice canônico*
