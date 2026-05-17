---
id: UX-BE-SESSION-STATE-SAFE
titulo: "Páginas Bem-estar com `session_state.pop` sem guard crashan em deep-link primeira visita"
status: concluída
concluida_em: 2026-05-17
prioridade: P2
data_criacao: 2026-05-17
fase: UX
epico: 5
depende_de: []
esforco_estimado_horas: 1
origem: "auditoria independente 2026-05-17. `src/dashboard/paginas/be_privacidade.py:385` usa `st.session_state.pop(_KEY_FLASH)` sem default. Em deep-link `?cluster=Bem-estar&tab=Privacidade` numa sessão fresca, `_KEY_FLASH` não existe → KeyError → 500 no Streamlit. Padrão similar pode estar em be_diario.py, be_eventos.py, be_marcos.py (12 abas Bem-estar)."
---

# Sprint UX-BE-SESSION-STATE-SAFE

## Contexto

Streamlit `st.session_state.pop(key)` levanta `KeyError` se a chave não existir. Já `pop(key, default)` retorna o default. Padrão seguro:

```python
flash = st.session_state.pop(_KEY_FLASH, None)
```

Audit revelou que `be_privacidade.py:385` chama:

```python
flash = st.session_state.pop(_KEY_FLASH)  # sem default
```

Outros candidatos a auditar (Bem-estar = 12 abas, várias com flash messages):
- `be_diario.py`, `be_eventos.py`, `be_marcos.py`
- `be_alarmes.py`, `be_contadores.py`, `be_ciclo.py`, `be_tarefas.py`
- `be_treinos.py`, `be_medidas.py`, `be_recap.py`

## Hipótese e validação ANTES

```bash
grep -rn "session_state.pop" src/dashboard/paginas/ | grep -v ", None\|, \"\"\|, 0\|, \[\]\|, {}\|, False" | head -10
# Esperado: vários pop() sem default
```

## Objetivo

1. **Auditar todas ocorrências** de `st.session_state.pop(chave)` em `paginas/`.

2. **Adicionar default** apropriado:
   ```python
   # Antes:
   flash = st.session_state.pop(_KEY_FLASH)
   # Depois:
   flash = st.session_state.pop(_KEY_FLASH, None)
   ```

3. **Pattern alternativo** quando default não é trivial:
   ```python
   if _KEY_FLASH in st.session_state:
       flash = st.session_state.pop(_KEY_FLASH)
       # render flash
   ```

4. **Testes regressivos**:
   - `test_pagina_privacidade_primeira_visita_nao_crasha`
   - `test_pagina_diario_deep_link_session_vazia`
   - Mock `st.session_state` com dict vazio + chamar `renderizar()` + assert sem exceção.

5. **Documentar pattern em `docs/CICLO_GRADUACAO_OPERACIONAL.md`** ou similar (padrão canônico do projeto).

## Não-objetivos

- Não criar wrapper `safe_pop()` global (over-engineering — `pop(k, None)` basta).
- Não tocar lógica de flash messages.
- Não tocar `st.session_state[chave]` reads (não levantam KeyError; retornam undefined que crasha de outra forma — sprint dedicada se aparecer).

## Proof-of-work runtime-real

```bash
# Buscar ocorrências problemáticas:
grep -rn "session_state\.pop([^,]*)" src/dashboard/paginas/ | grep -v "None\|, \"\"\|False\|, 0\|, \[\]\|, {}"

# Apos fix, count deve ser 0:
grep -rn "session_state\.pop(" src/dashboard/paginas/ | wc -l
```

## Acceptance

- ≤2 ocorrências de `pop(chave)` sem default em `paginas/` (essas com guard `if k in session_state`).
- 5+ testes regressivos verdes (deep-link primeira visita por aba Bem-estar).
- Pytest baseline mantida.

## Padrões aplicáveis

- (n) Defesa em camadas — guard + default.

---

*"Deep-link primeira visita é o teste mais cruel da UX." — princípio do entry point*
