# HANDOFF — sessão 2026-04-23 (rota "conserta tudo")

Sessão de auditoria profunda + refactor total pós-crash. Atualizado incrementalmente a cada avanço.

**Estado inicial:** HEAD em `19231e8` (docs sprints 92/93/94). Sessão anterior travou durante planejamento (não executou nada).

---

## Diagnóstico — Relatório de Auditoria (2026-04-23)

Auditoria de fidelidade em 760 arquivos `data/raw/` + inbox + XLSX + grafo.

### Corretos (OK)
- Batida XLSX 6088 / grafo 6086 transações.
- C6, Nubank (André e Vitória), Itaú (29 em 3 meses), Santander (110 em 6 meses), holerites (24 únicos), DAS (CNPJ 45.850.636 ANDRE confirmado).

### Críticos
- **CRÍT-1** — Aba `renda` contaminada: 459 linhas vs ~24 reais. Reembolsos PIX, transferências, cashback, PIX pessoais todos classificados como renda.
- **CRÍT-2** — Só 4 documentos no grafo (de ~80 físicos). ADR-20 tracking quebrado: 47 DAS + 3 certidões + 3 garantias + 24 holerites + 2 cupons não catalogados.
- **CRÍT-3** — pessoa_detector: 2.310 tx Nubank PF Vitória classificadas como "Casal"; 19 DAS + 3 certidões do André em `data/raw/casal/`.
- **CRÍT-4** — Roteador duplica arquivos (Itaú 5 únicos → 29 físicos; Santander 18 → 102).

### Médios
- **MED-1** — Inbox órfão: `05127373122-IRPF-A-2026-2025-RETIF.DEC` (formato `.DEC` sem extrator) + `notas de garantia e compras.pdf` (PDF-imagem 4p).
- **MED-2** — Pastas especiais: `_envelopes/originais/` (28 PDFs não classificados, ao menos 1 DAS do André); `_conferir/` (6 pastas de 2 cupons duplicados).
- **MED-3** — Fallback supervisor não-idempotente (bug uuid.uuid4() duplica em `docs/propostas/extracao_cupom/` E `data/raw/_conferir/`).

---

## Plano de execução (rota "conserta tudo")

### P0 — Blocker de qualidade de dados
- [x] **P0.1 — Fix aba `renda`**: restringir a holerites + receitas bancárias explícitas. **CONCLUÍDA.**
- [ ] **P0.2 — Sprint 90 pessoa_detector**: CPF Vitória + yaml + executor.

### P1 — Alto valor
- [ ] **P1.1 — Extrator DAS PARCSN**: +47 documentos no grafo.
- [ ] **P1.2 — Sprint 89 OCR fallback PDF-imagem**: fecha inbox.

### P2 — Higiene
- [ ] **P2.1 — Sprint 87d fallback idempotente**.
- [ ] **P2.2 — Sprint 91 UX v3** (6 fixes visuais).
- [ ] **P2.3 — Dedupe roteamento adapter**.

### P3 — Estratégico
- [ ] **P3.1 — Extrator DIRPF `.DEC`**.
- [ ] **P3.2 — Holerite vira node documento no grafo**.

---

## Log incremental de execução

### 2026-04-23 — Contexto restaurado
- Baseline verde: `make lint` OK / `pytest` 1139 passed / 10 skipped / `make smoke` 23/0 + 8/8.
- Revert do bullet em `grafo_obsidian.py:140` via `git checkout --`.
- Sprint 87d planejada (spec em `docs/sprints/backlog/sprint_87d_*.md`).
- Auditoria concluída (6 tasks). Relatório acima.

### 2026-04-23 — P0.1 concluída: fix aba renda (459 → 99 linhas)

Criados:
- `mappings/fontes_renda.yaml` — whitelist (salário CLT, MEI André PAIM/SUNO/F2/etc., bolsa NEES, rendimento aplicação) + blacklist (reembolso, estorno, cashback, PIX genérico, Aplicação/Resgate RDB, Brasil Bitcoin).
- `src/utils/fontes_renda.py` — helper com `eh_fonte_real_de_renda(descricao)`. Whitelist tem prioridade sobre blacklist (ex: "Transferência recebida pelo Pix - F2 MARKETING" casa ambos; whitelist vence).
- `tests/test_fontes_renda.py` — 30 testes cobrindo whitelist, blacklist, ambígua, prioridade.

Modificados:
- `src/load/xlsx_writer.py::_criar_aba_renda` — aplica filtro em receitas inferidas do extrato. Holerites do contracheque_pdf.py vão direto (autoritários).
- `scripts/smoke_aritmetico.py::contrato_receita_nao_exagera_salario` — aplica blacklist antes de somar receita, evitando falso-positivo quando reembolso/estorno infla total.

Runtime real pós-fix:
- Aba renda: 459 → **99 linhas** (24 holerites + 75 MEI legítimo).
- Smoke aritmético: 8/8 contratos OK (sem regressão nos outros 7).
- Pytest: 1139 → 1169 passed (+30 novos).
- Lint: OK.

### _Próximo: P0.2 (Sprint 90 pessoa_detector)_

---

## Artefatos criados nesta sessão

- `docs/sprints/backlog/sprint_87d_fallback_supervisor_idempotente_cupom.md`
- `docs/HANDOFF_2026-04-23_conserta_tudo.md` (este arquivo)
- `/home/andrefarias/.claude/plans/magical-dazzling-rain.md`

## Contratos preservados

- Gauntlet obrigatório antes de fechar cada sprint: `make lint` + pytest + `make smoke` + `finish_sprint.sh NN`.
- Commits PT-BR imperativos, sem menção a IA.
- Zero follow-up: ressalva vira sprint-ID ou Edit-pronto.
- HANDOFF atualizado a cada avanço para preservar estado contra crash.

---

*"Documentar é garantir que o próximo passo exista antes de cair." — princípio anti-crash*
