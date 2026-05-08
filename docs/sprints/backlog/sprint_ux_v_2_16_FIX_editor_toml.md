---
id: UX-V-2.16-FIX
titulo: Editor TOML — implementar layout 3-col + preview ao vivo + validação inline
status: backlog
prioridade: alta
data_criacao: 2026-05-08
fase: PARIDADE_VISUAL
depende_de: []
esforco_estimado_horas: 6
origem: docs/auditorias/AUDITORIA_PARIDADE_VISUAL_2026-05-08.md (página 28)
mockup: novo-mockup/mockups/28-rotina-toml.html
---

# Sprint UX-V-2.16-FIX — Editor TOML com 3-col completo

## Contexto

UX-V-2.16 declarou paridade (commits `e50eeb4 + 6619e6f merge(ux-v-2.16)`) mas o frontmatter ficou `status: backlog` e a inspeção 2026-05-08 mostra que metade da feature falta:

- Layout 2-col (lista + editor) em vez de 3-col (lista + editor + preview).
- Preview ao vivo ausente — mockup tem 3ª coluna com tabs Visual/Diff vs HEAD/Schema mostrando alarmes/tarefas/contadores renderizados a partir do TOML em edição.
- Badge MODIFICADO/SCHEMA OK no header do editor ausente.
- Linhas numeradas + syntax-highlight ausente (textarea simples).
- Bloco VALIDAÇÃO inline (0 erros, 1 aviso) ausente.

## Objetivo

1. Layout 3-col real (`st.columns([1, 2, 2])` ou similar).
2. Preview ao vivo: ler TOML do textarea (em memória), validar com schema, renderizar:
   - **Visual**: cards de alarme/tarefa/contador como `be_rotina` espera.
   - **Diff vs HEAD**: comparar com `git show HEAD:.ouroboros/rotina/<arquivo>.toml`.
   - **Schema**: mostrar schema canônico esperado.
3. Badge `MODIFICADO` (laranja) quando textarea diff vs disco; `SCHEMA OK` (verde) quando validação passa.
4. Linhas numeradas via wrapper CSS (sem mudar para Monaco/Ace).
5. Bloco VALIDAÇÃO no rodapé com erros/avisos.
6. Mover spec de `backlog/` para `concluidos/` ao fechar.

## Validação ANTES (grep)

```bash
wc -l src/dashboard/paginas/be_editor_toml.py
grep -n "st.columns\|preview\|validar\|MODIFICADO" src/dashboard/paginas/be_editor_toml.py | head
```

## Não-objetivos

- NÃO trocar `st.text_area` por Monaco/Ace.
- NÃO implementar persistência git auto-commit (botão Salvar (commit) já chama git).

## Proof-of-work

```bash
make lint && make smoke
.venv/bin/pytest tests/ -k editor_toml -q
```

Captura visual: cluster=Bem-estar&tab=Editor+TOML mostra 3-col, preview com 3 tabs, badges no header, validação rodapé.

## Critério de aceitação

1. Layout 3-col em viewport >=1280px.
2. Preview Visual renderiza alarme/tarefa/contador a partir do TOML em edição.
3. Tab Diff funcional comparando contra HEAD git.
4. Badges MODIFICADO/SCHEMA OK no header.
5. Bloco VALIDAÇÃO no rodapé com 0+ avisos.
6. Lint + smoke + baseline pytest.
7. Frontmatter da spec V-2.16 atualizado para `status: concluida`.

## Referência

- Spec original: `sprint_ux_v_2_16_editor_toml.md`.
- Mockup: `28-rotina-toml.html`.

*"Editor sem preview é texto cego." — princípio V-2.16-FIX*
