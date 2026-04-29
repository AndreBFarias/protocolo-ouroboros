---
concluida_em: 2026-04-21
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 59
  title: "Fix UX: chips de sugestão na Busca Global não injetam valor"
  touches:
    - path: src/dashboard/paginas/busca.py
      reason: "chips clicam mas não atualizam o input"
    - path: tests/test_busca_global.py
      reason: "teste de contrato do chip"
  n_to_n_pairs: []
  forbidden: []
  tests:
    - cmd: "make lint"
      timeout: 60
    - cmd: ".venv/bin/pytest tests/test_busca_global.py -v"
      timeout: 60
  acceptance_criteria:
    - "Clicar no chip 'neoenergia' na aba Busca Global popula o campo de input com 'neoenergia' e dispara a busca"
    - "Busca retorna resultados agrupados (fornecedores, documentos, transações, itens) quando há match"
    - "Aba Busca Global não mostra o prefixo numérico da sprint no título (remove '52')"
    - "Proof-of-work via screenshot Playwright: clicar 'neoenergia' mostra resultados"
  proof_of_work_esperado: |
    # Subir dashboard e testar via Playwright:
    make dashboard &
    sleep 5
    # navegar, clicar chip, screenshot do resultado — validador-sprint via skill validacao-visual
```

---

# Sprint 59 — Fix chips Busca Global

**Status:** CONCLUÍDA (2026-04-21)
**Prioridade:** P1
**Dependências:** nenhuma
**Issue:** AUDIT-2026-04-21-UX-1

## Resultado

- `src/dashboard/paginas/busca.py`: chips trocaram `disabled=True` por callback `_aplicar_chip_sugestao` (on_click) que grava `st.session_state["busca_termo_input"]` -- padrão canônico Streamlit, contorna A59-1 (`st.rerun` em callback = loop).
- Key do `st.text_input` renomeada para `busca_termo_input` (N-para-N com a chave do session_state), removido parâmetro `value` (Streamlit persiste sozinho via key).
- Prefixo "52" removido do título do hero (`hero_titulo_html("", "Busca Global", ...)`).
- `tests/test_busca_global.py` criado (8 testes cobrindo: callback seta session_state, chips não-disabled, key casa com session_state, título sem "52", ponta-a-ponta chip→busca com grafo fixture).
- `tests/test_dashboard_busca.py` atualizado (sincronização N-para-N da key).

## Proof-of-work

- `make lint` e `ruff check` limpos nos arquivos tocados (`src/dashboard/paginas/busca.py`, `tests/test_busca_global.py`, `tests/test_dashboard_busca.py`).
- `.venv/bin/pytest tests/test_busca_global.py tests/test_dashboard_busca.py -v`: 25 passed.
- Screenshot Playwright: `/tmp/ouroboros_busca_neoenergia_APOS_FIX.png` (sha256 `e1cb43b430931434b22bd5463868713543c15e12f2e42a4d8094fcdae29051a5`) — chip clicado popula input com "neoenergia" e renderiza 57 resultados com 5 fornecedores encontrados.

## Problema

Auditoria 2026-04-21 tentou clicar no chip "neoenergia" na aba Busca Global; botão acende mas não popula o input. Funcionalidade principal da Sprint 52 (busca global doc-cêntrica) parcialmente morta.

## Implementação

Trocar onClick dos chips para usar `st.session_state["busca_termo"] = "neoenergia"` e `st.rerun()`.

Padrão canônico Streamlit:

```python
if st.button("neoenergia", key="chip_neoenergia"):
    st.session_state["busca_termo"] = "neoenergia"
    st.rerun()

termo = st.text_input(
    "Busca global",
    value=st.session_state.get("busca_termo", ""),
    key="busca_termo_input",
)
```

Além do fix: remover o "52" do título da página (já previsto na Sprint 63 — fazer aqui como n_to_n).

## Armadilhas Conhecidas

| A59-1 | `st.rerun()` em callback inline causa loop infinito | Usar padrão de callback separado |
| A59-2 | key do text_input colidindo com session_state key | Usar keys distintas |

## Evidências Obrigatórias

- [ ] Screenshot Playwright mostrando resultados após clicar chip
- [ ] Teste unitário do estado de sessão

---

*"Clicar e nada acontecer é pior que não ter botão." — princípio de UX*
