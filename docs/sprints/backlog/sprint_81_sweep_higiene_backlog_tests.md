## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 81
  title: "Sweep higiene: acentuação em tests/test_dashboard_titulos.py + ruff em scripts/ + noqa residual"
  touches:
    - path: tests/test_dashboard_titulos.py
      reason: "linha 8: 'numero' sem acento em docstring literal (AC-69-1, AC-61-1)"
    - path: Makefile
      reason: "incluir scripts/ no target lint (opt-in controlado)"
    - path: scripts/reprocessar_documentos.py
      reason: "ajustar E402 com noqa explícito OU refatorar imports"
  n_to_n_pairs: []
  forbidden: []
  tests:
    - cmd: "make lint"
      timeout: 60
    - cmd: ".venv/bin/pytest tests/ -q"
      timeout: 120
  acceptance_criteria:
    - "make lint exit 0 no working tree limpo"
    - "Nenhum falso-positivo de acentuação em arquivos PT-BR humanos"
    - "Identificadores técnicos N-para-N com schema do grafo mantidos sem acento + # noqa: accent"
    - "scripts/ entra no lint OU documentado opt-out em CLAUDE.md"
  proof_of_work_esperado: |
    make lint
    echo "exit=$?"  # esperado 0
    .venv/bin/pytest tests/ -q | tail -3
```

---

# Sprint 81 — Sweep higiene

**Status:** BACKLOG
**Prioridade:** P3
**Dependências:** nenhuma
**Issue:** INFRA-POS-AUDITORIA

## Problema

Após sprints 55-69 + 65, 66, 68b, 3 achados colaterais foram registrados sem fix inline (protocolo anti-débito):

- **AC-69-1 / AC-61-1**: `tests/test_dashboard_titulos.py:8` tem `numero` sem acento em docstring literal.
- **AC-62-A**: Violações em `src/transform/categorizer.py` relacionadas a `classificacao` em comentários (Sprint 67 resolveu parcialmente).
- **AC-66-1**: Falha `test_nivel3_par_transferencia_marca_ambos_lados` — relacionada a Sprint 68b (ainda em execução no momento da redação).
- **AC-69-2**: `scripts/reprocessar_documentos.py` tem 14 erros de ruff (E402 em imports pós `sys.path.insert`). Decidir se scripts/ entra no `make lint` ou fica opt-out.

Sprint 81 varre e limpa.

## Implementação

Caso a caso:

1. `tests/test_dashboard_titulos.py:8` — adicionar `# noqa: accent` na linha OU reescrever docstring sem citar o nome do parâmetro literalmente.
2. `scripts/reprocessar_documentos.py` — adicionar `# noqa: E402` após `sys.path.insert()` em todos os imports, OU mover `sys.path.insert` para topo dos imports.
3. Makefile: decidir entre:
   - **Opção A:** `make lint` passa a rodar `ruff check src/ tests/ scripts/` (mais rigor, mais trabalho).
   - **Opção B:** documentar em CLAUDE.md que `scripts/` é opt-out de ruff (mais flexível para scripts de orquestração).

Decisão recomendada: **Opção A** com `# noqa` explícito onde necessário — rigor consistente.

## Evidências

- [ ] `make lint` exit 0 sem nenhuma exception
- [ ] Zero violação residual de acentuação em prosa humana
- [ ] Documentação atualizada se Opção B

---

*"Tudo limpo antes de entrar na Fase IOTA." — princípio"*
