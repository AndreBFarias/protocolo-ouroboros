## 0. SPEC (machine-readable)

```yaml
sprint:
  id: INFRA-CONSOLIDA-V2
  title: "Consolidar 3 ressalvas colaterais do cluster UX v2 (acentuacao + monkeypatch + regex padding)"
  prioridade: P3
  estimativa: 50min
  origem: "achados colaterais dos executores UX-122, UX-123, UX-124"
  pre_requisito_de: []
  touches:
    # AC1: acentuacao em specs
    - path: docs/sprints/concluidos/sprint_UX_119_polish_combo_v2.md
      reason: "fix violacoes de acentuacao em texto PT-BR (nao/sao/canonico/etc.)"
    - path: docs/sprints/concluidos/sprint_UX_121_rename_hoje_home.md
      reason: "fix acentuacao"
    - path: docs/sprints/concluidos/sprint_UX_122_remover_prefixos_numericos.md
      reason: "fix acentuacao"
    - path: docs/sprints/concluidos/sprint_UX_123_home_cross_tabs.md
      reason: "fix acentuacao"
    - path: docs/sprints/concluidos/sprint_UX_124_busca_inline_table.md
      reason: "fix acentuacao"
    # AC2: monkeypatch em test_dashboard_revisor
    - path: tests/test_dashboard_revisor.py
      reason: "linhas 187,201 fazem 'd.listar_pendencias_revisao = _stub_listar' diretamente; trocar por monkeypatch.setattr(d, 'listar_pendencias_revisao', _stub_listar) com fixture pytest"
    # AC3: regex padding
    - path: tests/test_ux_tokens.py
      reason: "test_css_global_declara_padding_bloco usa regex 'padding: Npx' que nao casa apos UX-116/119 separarem em padding-top/right/bottom/left; relaxar para aceitar qualquer das 4 propriedades"
  forbidden:
    - "Mudar conteudo logico das specs (so corrige acentuacao)"
    - "Mudar comportamento dos testes (so como atribuem stubs)"
    - "Adicionar deps externas"
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/test_dashboard_revisor.py tests/test_revisor.py tests/test_ux_tokens.py -v"
    - cmd: ".venv/bin/pytest tests/ -q"
    - cmd: "make smoke"
  acceptance_criteria:
    # AC1: 0 violacoes em make lint apos fix
    - "make lint exit 0 em main com cluster v2 + INFRA-CONSOLIDA-V2 mergeada"
    - "scripts/check_acentuacao.py --paths docs/sprints/concluidos/sprint_UX_*.md retorna exit 0"
    # AC2: monkeypatch
    - "tests/test_dashboard_revisor.py usa monkeypatch.setattr para stubs (sem atribuicoes diretas no modulo dados)"
    - "Suite full pytest: tests/test_revisor.py::TestListarPendencias::* TODOS passam (4 testes que falhavam em main)"
    # AC3: regex relaxada
    - "tests/test_ux_tokens.py::test_css_global_declara_padding_bloco aceita 'padding-top: Npx' (regex relaxada, mantendo invariante de PADDING_INTERNO presente)"
    - "Suite full pytest: 0 falhas alem do INFRA-97a flaky conhecido"
  proof_of_work_esperado: |
    # AC1
    .venv/bin/python scripts/check_acentuacao.py --paths docs/sprints/concluidos/sprint_UX_119_polish_combo_v2.md docs/sprints/concluidos/sprint_UX_121_rename_hoje_home.md docs/sprints/concluidos/sprint_UX_122_remover_prefixos_numericos.md docs/sprints/concluidos/sprint_UX_123_home_cross_tabs.md docs/sprints/concluidos/sprint_UX_124_busca_inline_table.md
    # = exit 0

    # AC2
    .venv/bin/pytest tests/test_revisor.py::TestListarPendencias -v
    # = 4 passed (em suite full tambem, nao so isolado)

    # AC3
    .venv/bin/pytest tests/test_ux_tokens.py -v
    # = todos passed

    # Suite full
    .venv/bin/pytest tests/ -q
    # = 0 falhas alem de INFRA-97a flaky
```

---

# Sprint INFRA-CONSOLIDA-V2 -- Consolidar 3 ressalvas

**Status:** CONCLUÍDA (commit `7f78887`, 2026-04-27 — 5 testes que falhavam agora passam; suite full 1817/1817)

3 ressalvas detectadas pelos executores do cluster v2 que não bloquearam merge das sprints respectivas mas deixaram main com falhas pequenas:

1. **Acentuacao em 5 specs UX**: `make lint` falha em main por 8 violacoes em texto PT-BR (`nao`/`sao`/`pagina`/`historico`/`numerico` etc.).
2. **Contaminação de testes em revisor**: atribuicao direta `d.listar_pendencias_revisao = stub` em `test_dashboard_revisor.py` persiste entre testes, contaminando 4 testes de `test_revisor.py::TestListarPendencias` em suite full.
3. **Regex padding desatualizada**: `test_ux_tokens.py::test_css_global_declara_padding_bloco` usa regex `padding: Npx` shorthand que UX-116 separou em `padding-top/right/bottom/left`.

Sprint cirurgica: 3 fixes pequenos, 1 commit por fix preferencialmente (3 commits no branch ou 1 commit conjugado).

---

*"Débito acumulado por achados colaterais não deve virar refrão -- consolida em 1 sprint enxuta." -- princípio do anti-débito*
