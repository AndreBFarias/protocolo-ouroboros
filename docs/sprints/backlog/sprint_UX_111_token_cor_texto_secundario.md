## 0. SPEC (machine-readable)

```yaml
sprint:
  id: UX-111
  title: "Token de cor texto_sec: #6272A4 -> #c9c9cc"
  prioridade: P1
  estimativa: 1h
  origem: "feedback dono 2026-04-27 -- contraste do texto secundario insuficiente em monitor de baixo brilho"
  pre_requisito_de: [100]
  touches:
    - path: src/dashboard/tema.py
      reason: "trocar DRACULA['comment'] de #6272A4 para #c9c9cc; afeta CORES['texto_sec'] e CORES['na']"
    - path: src/dashboard/componentes/grafo_pyvis.py
      reason: "se referencia direta ao hex literal, atualizar"
    - path: src/load/formatacao_md.py
      reason: "se referencia direta, atualizar"
    - path: tests/test_dashboard_tema.py
      reason: "regressao: CORES['texto_sec'] == '#c9c9cc'"
  forbidden:
    - "Mudar outros tokens (Dracula original preservado conceitualmente; so o overload do projeto)"
    - "Tocar em #6272A4 fora dos arquivos do dashboard (ex: docs/ historicas, mockups/)"
    - "Deixar referencias hardcoded ao hex em codigo de produto novo -- sempre via token CORES['texto_sec']"
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/test_dashboard*.py -q"
    - cmd: "make smoke"
  acceptance_criteria:
    - "DRACULA['comment'] em src/dashboard/tema.py = '#c9c9cc'"
    - "Grep -rin '6272A4' em src/dashboard/ retorna 0 resultados (todas as referencias usam token)"
    - "Grep '6272A4' em src/load/, mockups/ pode permanecer (escopo limitado a dashboard)"
    - "Teste regressivo verifica CORES['texto_sec'] == '#c9c9cc'"
    - "Validacao visual humana: textos secundarios mais legiveis em fundo escuro"
  proof_of_work_esperado: |
    # Antes
    grep -n '6272A4' src/dashboard/tema.py
    # = linha 23

    # Depois
    grep -n 'c9c9cc' src/dashboard/tema.py
    # = linha 23
    grep -rin '6272A4' src/dashboard/
    # = 0 resultados em codigo (so referencias historicas em docs/)

    # Captura visual (skill validacao-visual + validacao humana)
```

---

# Sprint UX-111 -- Token de cor texto_sec

**Status:** BACKLOG (P1, criada 2026-04-27, pré-requisito da Sprint 100)

Hoje `DRACULA['comment'] = "#6272A4"` propaga para `CORES['texto_sec']` e `CORES['na']` (`src/dashboard/tema.py:23,37,47`). Substituir por `#c9c9cc` melhora contraste em telas de baixo brilho.

---

*"Token único > literal espalhado. Mudar a cor uma vez muda em todo lugar." -- princípio do design system honesto*
