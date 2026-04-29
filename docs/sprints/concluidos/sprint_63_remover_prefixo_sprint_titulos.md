---
concluida_em: 2026-04-21
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 63
  title: "Remover prefixo numérico de sprint dos títulos das páginas"
  touches:
    - path: src/dashboard/paginas/catalogacao.py
      reason: "título exibe '51 Catalogação de Documentos'"
    - path: src/dashboard/paginas/busca.py
      reason: "título exibe '52 Busca Global'"
    - path: src/dashboard/paginas/grafo_obsidian.py
      reason: "título exibe '53 Grafo Visual + Obsidian'"
    - path: tests/test_dashboard_titulos.py
      reason: "teste que nenhum título começa com dígitos"
  n_to_n_pairs: []
  forbidden: []
  tests:
    - cmd: "make lint"
      timeout: 60
    - cmd: ".venv/bin/pytest tests/test_dashboard_titulos.py -v"
      timeout: 30
  acceptance_criteria:
    - "Título visível da aba Catalogação é 'Catalogação de Documentos' (sem '51')"
    - "Título visível da aba Busca é 'Busca Global' (sem '52')"
    - "Título visível da aba Grafo é 'Grafo Visual + Obsidian' (sem '53')"
    - "Teste automatizado falha se qualquer título começar com dígito"
  proof_of_work_esperado: |
    grep -rn "st.header\|st.title" src/dashboard/paginas/ | grep -E "[0-9]{2,3}"
    # Esperado: zero matches
```

---

# Sprint 63 — Títulos limpos

**Status:** BACKLOG
**Prioridade:** P2
**Issue:** AUDIT-2026-04-21-UX-7

## Problema

Auditoria viu "51 Catalogação de Documentos", "52 Busca Global", "53 Grafo Visual + Obsidian" nos títulos. Vazamento do ID da sprint no UI de produção. Usuário não precisa saber qual sprint criou aquilo.

## Implementação

Buscar nos 3 arquivos `src/dashboard/paginas/{catalogacao,busca,grafo_obsidian}.py` o prefixo numérico e remover.

Provável pattern: `st.header(f"{SPRINT_ID} Busca Global")` ou similar.

Teste:

```python
def test_nenhum_titulo_comeca_com_digito():
    import re
    for f in Path("src/dashboard/paginas").glob("*.py"):
        src = f.read_text()
        assert not re.search(r'st\.(header|title|subheader)\(["\'][\s]*\d+\s', src), \
            f"{f.name} tem título começando com dígito"
```

## Evidências Obrigatórias

- [ ] Screenshot das 3 abas sem número prefixo
- [ ] Teste automatizado

---

*"Produção não é changelog." — princípio de release*
