---
id: UX-V-2.16
titulo: Editor TOML 3-col (lista arquivos + editor + preview ao vivo)
status: concluida  <!-- noqa: accent -->
prioridade: alta
data_criacao: 2026-05-07
concluida_em: 2026-05-07  <!-- noqa: accent -->
commit: 6619e6f
fase: PARIDADE_VISUAL
depende_de: [UX-V-02]
co_executavel_com: [UX-V-2.8, UX-V-2.10, UX-V-2.14]
esforco_estimado_horas: 6
origem: docs/auditorias/AUDITORIA_PARIDADE_VISUAL_2026-05-07.md (página 28)
mockup: novo-mockup/mockups/28-rotina-toml.html
nota: paridade parcial -- preview com tabs/badges/diff entregue em UX-V-2.16-FIX
---

# Sprint UX-V-2.16 -- Editor TOML 3-col + preview ao vivo

## Contexto

Auditoria: dashboard atual mostra editor único de `rotina.toml`. Mockup tem layout 3-col:
- Lista arquivos esquerda (manha/tarde/noite/medicacao/fim-de-semana.toml)
- Editor central syntax-highlighted
- Preview ao vivo direita (Visual / Diff / Schema com tabs) + Validação inline + "Vai afetar"

## Página afetada

`src/dashboard/paginas/be_editor_toml.py` apenas.

## Objetivo

1. Layout 3-col: lista arquivos | editor | preview ao vivo.
2. Lista mostra todos `.toml` em `<vault>/.ouroboros/rotina/` com counts (alarmes/tarefas).
3. Editor central preserva o `st.text_area` atual.
4. Preview ao vivo renderiza visual dos alarmes/tarefas/contadores parseados do TOML em tempo real.
5. Validação inline (0 erros / N avisos) baseada em parsing tomllib.

## Validação ANTES

```bash
wc -l src/dashboard/paginas/be_editor_toml.py
grep -n "tomllib\|^def \|st.text_area" src/dashboard/paginas/be_editor_toml.py | head -10
```

## Spec de implementação

```python
import tomllib

def _listar_arquivos_toml(vault_root: Path | None) -> list[dict]:
    """Lista .toml em <vault>/.ouroboros/rotina/ com contagens."""
    if vault_root is None:
        return []
    pasta = vault_root / ".ouroboros" / "rotina"
    if not pasta.exists():
        return []
    items = []
    for arq in sorted(pasta.glob("*.toml")):
        try:
            d = tomllib.loads(arq.read_text(encoding='utf-8'))
            n = sum(len(d.get(k, [])) for k in ['alarme', 'tarefa', 'contador'])
        except Exception:
            n = 0
        items.append({"path": str(arq), "nome": arq.stem, "count": n})
    return items


def _validar_toml(conteudo: str) -> tuple[int, int, list[str]]:
    """Retorna (n_erros, n_avisos, mensagens)."""
    msgs = []
    try:
        d = tomllib.loads(conteudo)
    except tomllib.TOMLDecodeError as e:
        return 1, 0, [f"erro de sintaxe: {e}"]
    # Avisos: alarme sem `som`, tarefa sem `prioridade`, etc.
    for a in d.get('alarme', []):
        if not a.get('som'):
            msgs.append(f"alarme '{a.get('nome', '?')}' sem 'som'")
    return 0, len(msgs), msgs


def _preview_visual_html(conteudo: str) -> str:
    """Renderiza visual dos itens parseados do TOML."""
    try:
        d = tomllib.loads(conteudo)
    except tomllib.TOMLDecodeError:
        return '<p class="preview-erro">TOML inválido — corrija sintaxe.</p>'
    
    items = []
    for a in d.get('alarme', []):
        items.append(f'<div class="prev-alarme">{a.get("hora", "?")} · {a.get("nome", "?")}</div>')
    for t in d.get('tarefa', []):
        items.append(f'<div class="prev-tarefa">☐ {t.get("nome", "?")}</div>')
    for c in d.get('contador', []):
        items.append(f'<div class="prev-contador">{c.get("nome", "?")} · meta {c.get("meta", "?")}</div>')
    
    if not items:
        return '<p class="preview-vazio">Sem itens para preview.</p>'
    return minificar(f'<div class="preview-bloco">{"".join(items)}</div>')
```

Render 3 columns:

```python
col_lista, col_editor, col_preview = st.columns([1, 2, 2])
with col_lista:
    arquivos = _listar_arquivos_toml(vault_root)
    if not arquivos:
        st.info("Sem .toml em <vault>/.ouroboros/rotina/")
    else:
        for arq in arquivos:
            st.markdown(f"<div class='lista-item'>{arq['nome']} <span class='count'>{arq['count']}</span></div>", unsafe_allow_html=True)
        nome_sel = st.selectbox("Arquivo", [a['nome'] for a in arquivos])
        path_sel = next(a['path'] for a in arquivos if a['nome'] == nome_sel)
        conteudo = Path(path_sel).read_text(encoding='utf-8')

with col_editor:
    novo_conteudo = st.text_area("Editor", conteudo, height=400)
    erros, avisos, msgs = _validar_toml(novo_conteudo)
    badge = '<span class="ok">✓ schema OK</span>' if erros == 0 else f'<span class="erro">✗ {erros} erros</span>'
    st.markdown(f"<div class='validacao-inline'>{badge} · {avisos} avisos</div>", unsafe_allow_html=True)
    if msgs:
        for m in msgs:
            st.markdown(f"<div class='msg'>{m}</div>", unsafe_allow_html=True)

with col_preview:
    st.markdown("<h3 class='preview-titulo'>PREVIEW AO VIVO</h3>", unsafe_allow_html=True)
    st.markdown(_preview_visual_html(novo_conteudo), unsafe_allow_html=True)
```

## CSS em `src/dashboard/css/paginas/be_editor_toml.css`

```css
.lista-item {
    display: flex; justify-content: space-between;
    padding: 4px var(--sp-2); font-family: var(--ff-mono); font-size: 12px;
    border-radius: var(--r-xs);
}
.lista-item:hover { background: var(--bg-elevated); }
.lista-item .count {
    color: var(--text-muted); font-size: 10px;
}

.validacao-inline {
    font-family: var(--ff-mono); font-size: 11px;
    padding: 4px var(--sp-2); margin-top: var(--sp-2);
}
.validacao-inline .ok { color: var(--accent-green); }
.validacao-inline .erro { color: var(--accent-red); }

.preview-bloco {
    background: var(--bg-surface); border: 1px solid var(--border-subtle);
    border-radius: var(--r-md); padding: var(--sp-3);
    font-family: var(--ff-mono); font-size: 12px;
}
.prev-alarme { color: var(--accent-orange); padding: 2px 0; }
.prev-tarefa { color: var(--text-secondary); padding: 2px 0; }
.prev-contador { color: var(--accent-cyan); padding: 2px 0; }
.preview-vazio, .preview-erro {
    font-family: var(--ff-mono); font-size: 12px;
    color: var(--text-muted); padding: var(--sp-3);
}
.preview-erro { color: var(--accent-red); }
```

## Validação DEPOIS

```bash
make lint && make smoke
.venv/bin/python -m pytest tests/test_be_editor*.py -q
```

## Proof-of-work runtime-real

Validação visual em `cluster=Bem-estar&tab=Editor+TOML`. Mostrar 3 colunas com lista + editor + preview ao vivo.

## Critério de aceitação

1. 3 colunas renderizando.
2. Lista de arquivos com counts.
3. Validação inline.
4. Preview ao vivo atualizando.
5. CSS criado.
6. Lint OK + cluster pytest verde.

## Não-objetivos

- NÃO implementar persistência via git automático (escopo separado).
- NÃO mexer em outras páginas.

## Referência

- Mockup: `novo-mockup/mockups/28-rotina-toml.html`.
- VALIDATOR_BRIEF: `(a)/(b)/(k)/(o)/(u)`.

*"Texto é a interface mais honesta." -- princípio V-2.16*
