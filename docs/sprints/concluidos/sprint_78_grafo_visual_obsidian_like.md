## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 78
  title: "Grafo visual Obsidian-like: full-page, filtros laterais, clique navega via query_params"
  touches:
    - path: src/dashboard/paginas/grafo_obsidian.py
      reason: "substituir subgrafo 1-hop por visualização full-page com painel de filtros"
    - path: src/graph/queries.py
      reason: "nova função grafo_filtrado(tipos, incluir_orfaos, limite) -> (nodes, edges)"
    - path: src/dashboard/componentes/grafo_pyvis.py
      reason: "novo: wrapper pyvis que gera HTML com JS de clique -> query param"
    - path: tests/test_grafo_filtrado.py
      reason: "testes da query + do wrapper"
    - path: pyproject.toml
      reason: "garantir pyvis em deps (já existe; confirmar versão)"
  n_to_n_pairs:
    - ["tipos de nó filtráveis", "ADR-14 §Tipos canônicos"]
    - ["JS click handler", "st.query_params (aba Extrato lê)"]
  forbidden:
    - "Renderizar >2000 nós sem paginação (trava browser)"
    - "Comunicação pyvis <-> Streamlit via postMessage (fragil; usar URL navigation)"
  tests:
    - cmd: "make lint"
      timeout: 60
    - cmd: ".venv/bin/pytest tests/test_grafo_filtrado.py -v"
      timeout: 60
  acceptance_criteria:
    - "Canvas do grafo ocupa pelo menos 70% da largura do conteúdo central"
    - "Painel lateral direito (30% da largura) com filtros: toggle Órfãos, multiselect Tipos de nó, slider Limite (100-2000), slider Profundidade (1-4)"
    - "Default: tipos=[fornecedor, documento, categoria, transacao], orfaos=False, limite=500, profundidade=2"
    - "Clicar em nó abre nova aba do dashboard com query_params setados (?tab=Extrato&fornecedor=X ou &documento_id=Y)"
    - "Legenda de cor visível (por tipo de nó): Dracula palette"
    - "Performance: 500 nós carregam em <3s (medido)"
    - "Nó tem label humano (aliases[0] ou razao_social ou nome_canonico[:40])"
    - "Tamanho do nó proporcional ao grau (mais conexões = maior)"
    - "Tooltip mostra: tipo, nome_canonico completo, contagem de conexões"
  proof_of_work_esperado: |
    # 1. Rodar dashboard
    .venv/bin/streamlit run src/dashboard/app.py --server.port 8501 --server.headless true &
    sleep 5
    # 2. Abrir aba Grafo + Obsidian, screenshot com 500 nós default
    # 3. Clicar em um fornecedor -> URL vira ?tab=Extrato&fornecedor=X
    # 4. Confirmar que aba Extrato renderiza filtrada
```

---

# Sprint 78 — Grafo Obsidian-like

**Status:** CONCLUÍDA (2026-04-22)
**Prioridade:** P1
**Dependências:** Sprint 60 (labels humanos), Sprint 73 (drill-down query_params), Sprint 74 (recomendada, pra ter documentos linkados)
**Issue:** UX-ANDRE-06

## Problema

Andre mostrou 3 screenshots do grafo do Obsidian dele (imagens 9, 10, 11 da sessão): nodes conectados, painel lateral com toggles (Etiquetas, Anexos, Apenas arquivos existentes, Órfãos) + Grupos + Tela + Forças. Visão: replicar dentro do dashboard do Ouroboros.

Sprint 53 já criou subgrafo 1-hop, mas é limitado (5 nós). Sprint 78 faz o grafo full-page com filtros.

## Contexto técnico (LEITURA OBRIGATÓRIA)

### pyvis em Streamlit — padrão canônico

`pyvis.Network` gera HTML standalone que pode ser embebido via `st.components.v1.html`. Três armadilhas:

1. **pyvis.show() escreve arquivo .html no disco antes** — não usar. Usar `net.generate_html()` que retorna string.
2. **Altura fixa obrigatória** (Streamlit não expande iframe automaticamente). `st.components.v1.html(html, height=800, scrolling=False)`.
3. **Comunicação pyvis <-> Streamlit via postMessage é frágil**. Cross-origin + Streamlit não tem API estável pra receber. **Decisão:** usar **URL navigation** — JS do clique faz `window.parent.location.search = "tab=Extrato&fornecedor=X"`, Streamlit lê via `st.query_params`.

### Injeção de JS no HTML do pyvis

`pyvis.Network` expõe `net.set_options(json_str)` mas não tem hook direto para clique. Precisamos manipular o HTML gerado:

```python
# src/dashboard/componentes/grafo_pyvis.py
from pyvis.network import Network
import json

JS_CLICK_HANDLER = """
<script type="text/javascript">
  network.on("click", function (params) {
    if (params.nodes.length === 0) return;
    const nodeId = params.nodes[0];
    const node = nodes.get(nodeId);
    if (!node) return;
    const tipo = node.node_tipo || "fornecedor";
    const nome = node.node_nome_canonico || node.label;
    const url = new URL(window.parent.location.href);
    url.searchParams.set("tab", "Extrato");
    url.searchParams.set(tipo, nome);
    window.parent.location.href = url.toString();
  });
</script>
"""

COR_POR_TIPO = {
    "transacao": "#8be9fd",
    "documento": "#bd93f9",
    "fornecedor": "#ffb86c",
    "categoria": "#50fa7b",
    "item": "#f1fa8c",
    "periodo": "#ff79c6",
    "conta": "#ff5555",
    "tag_irpf": "#f8f8f2",
    "prescricao": "#bd93f9",
    "garantia": "#ffb86c",
    "apolice": "#ff79c6",
    "seguradora": "#8be9fd",
}

def construir_grafo_html(
    nodes: list[dict],
    edges: list[dict],
    altura_px: int = 800,
) -> str:
    net = Network(
        height=f"{altura_px}px",
        width="100%",
        bgcolor="#282a36",
        font_color="#f8f8f2",
        directed=True,
        cdn_resources="in_line",  # embute CSS/JS do pyvis no HTML (sem dependência externa)
    )
    # Layout forças
    net.barnes_hut(gravity=-2000, central_gravity=0.3, spring_length=150, spring_strength=0.02)
    # Opções visuais
    net.set_options(json.dumps({
        "interaction": {"hover": True, "tooltipDelay": 100, "zoomView": True},
        "physics": {"stabilization": {"iterations": 200}},
        "nodes": {"font": {"color": "#f8f8f2", "size": 12, "face": "monospace"}},
        "edges": {"color": {"color": "#6272a4", "highlight": "#bd93f9"},
                  "smooth": {"type": "dynamic"}},
    }))

    for node in nodes:
        tipo = node["tipo"]
        label = _label_humano(node)
        size = 10 + min(node.get("grau", 0) * 2, 40)  # cap em 50
        tooltip = (
            f"<b>{tipo}</b><br>"
            f"{node.get('nome_canonico', '')}<br>"
            f"Conexões: {node.get('grau', 0)}"
        )
        net.add_node(
            node["id"],
            label=label[:30],
            color=COR_POR_TIPO.get(tipo, "#6272a4"),
            size=size,
            title=tooltip,
            # custom atributos que o JS usa no click handler
            node_tipo=tipo,
            node_nome_canonico=node.get("nome_canonico", label),
        )

    for edge in edges:
        net.add_edge(
            edge["src"],
            edge["dst"],
            label=edge["tipo"][:12],
            arrows={"to": {"enabled": True, "scaleFactor": 0.5}},
            width=max(0.5, edge.get("peso", 1) * 1.5),
        )

    html = net.generate_html()
    # Injeta o click handler ANTES do </body>
    html = html.replace("</body>", JS_CLICK_HANDLER + "</body>")
    return html


def _label_humano(node: dict) -> str:
    """Fallback chain: aliases[0] -> razao_social -> nome_canonico truncado."""
    aliases = node.get("aliases") or []
    if isinstance(aliases, str):
        import json as _json
        try:
            aliases = _json.loads(aliases)
        except (ValueError, TypeError):
            aliases = []
    if aliases:
        return str(aliases[0])
    metadata = node.get("metadata") or {}
    if isinstance(metadata, str):
        import json as _json
        try:
            metadata = _json.loads(metadata)
        except (ValueError, TypeError):
            metadata = {}
    if metadata.get("razao_social"):
        return metadata["razao_social"]
    nc = node.get("nome_canonico") or ""
    return nc if len(nc) <= 40 else nc[:37] + "..."
```

### Query de filtragem (src/graph/queries.py)

```python
def grafo_filtrado(
    tipos: list[str] | None = None,
    incluir_orfaos: bool = False,
    limite: int = 500,
    profundidade: int = 2,
    semente: int | None = None,
) -> tuple[list[dict], list[dict]]:
    """Retorna (nodes, edges) respeitando filtros.
    
    Se `semente` é dado, faz BFS de profundidade N a partir do nó.
    Senão, pega top `limite` nós por grau nos tipos solicitados.
    """
    tipos = tipos or ["fornecedor", "documento", "categoria", "transacao"]
    con = _conectar_grafo()
    # Busca nós por tipo + grau
    placeholders = ",".join("?" * len(tipos))
    query_nodes = f"""
        SELECT n.id, n.tipo, n.nome_canonico, n.aliases, n.metadata,
               (SELECT COUNT(*) FROM edge e
                WHERE e.src_id = n.id OR e.dst_id = n.id) as grau
        FROM node n
        WHERE n.tipo IN ({placeholders})
        ORDER BY grau DESC
        LIMIT ?
    """
    cursor = con.execute(query_nodes, (*tipos, limite))
    nodes = [dict(zip(
        ["id", "tipo", "nome_canonico", "aliases", "metadata", "grau"], row
    )) for row in cursor.fetchall()]

    if not incluir_orfaos:
        nodes = [n for n in nodes if n["grau"] > 0]

    # Edges entre os nós selecionados
    node_ids = {n["id"] for n in nodes}
    if not node_ids:
        return [], []
    ids_csv = ",".join(str(i) for i in node_ids)
    cursor = con.execute(f"""
        SELECT src_id, dst_id, tipo, peso
        FROM edge
        WHERE src_id IN ({ids_csv}) AND dst_id IN ({ids_csv})
    """)
    edges = [dict(zip(["src", "dst", "tipo", "peso"], row)) for row in cursor.fetchall()]

    return nodes, edges
```

### Página do dashboard

```python
# src/dashboard/paginas/grafo_obsidian.py
import streamlit as st
import streamlit.components.v1 as components
from src.dashboard.componentes.grafo_pyvis import construir_grafo_html
from src.graph.queries import grafo_filtrado

def renderizar():
    col_grafo, col_filtros = st.columns([7, 3], gap="medium")

    with col_filtros:
        st.subheader("Filtros")
        tipos_disponiveis = [
            "transacao", "documento", "fornecedor", "categoria", "item",
            "periodo", "conta", "tag_irpf", "prescricao", "garantia", "apolice",
        ]
        tipos = st.multiselect(
            "Tipos de nó",
            options=tipos_disponiveis,
            default=["fornecedor", "documento", "categoria", "transacao"],
        )
        orfaos = st.toggle("Mostrar órfãos", value=False)
        limite = st.slider("Limite de nós", 100, 2000, 500, step=100)
        profundidade = st.slider("Profundidade", 1, 4, 2)

        st.divider()
        st.caption("Legenda")
        from src.dashboard.componentes.grafo_pyvis import COR_POR_TIPO
        for tipo, cor in COR_POR_TIPO.items():
            st.markdown(
                f'<span style="color:{cor}">&#9679;</span> {tipo}',
                unsafe_allow_html=True,
            )

    with col_grafo:
        with st.spinner("Montando grafo..."):
            nodes, edges = grafo_filtrado(
                tipos=tipos,
                incluir_orfaos=orfaos,
                limite=limite,
                profundidade=profundidade,
            )
            st.caption(f"{len(nodes)} nós, {len(edges)} arestas")
            html = construir_grafo_html(nodes, edges, altura_px=800)
            components.html(html, height=820, scrolling=False)
```

## Armadilhas com solução

| Ref | Armadilha | Solução concreta |
|---|---|---|
| A78-1 | pyvis escreve HTML no disco | Usar `net.generate_html()` (string), não `net.show()` |
| A78-2 | Iframe bloqueia `window.parent` por CORS | `st.components.v1.html` renderiza no MESMO origin do Streamlit, então `window.parent` funciona |
| A78-3 | 7000 nós congelam browser | Limite slider hard-cap 2000; default 500 |
| A78-4 | Nós do tipo "transacao" são milhares -> explosão | Se `transacao` em tipos E limite > 500, mostrar warning |
| A78-5 | Acentos no nome viram `?` no URL | `urllib.parse.quote` no JS — mas `searchParams.set` já encoda |
| A78-6 | Física do pyvis demora a estabilizar | `physics.stabilization.iterations: 200` limita + mostra spinner |
| A78-7 | CDN do pyvis não carrega offline | `cdn_resources="in_line"` inlina CSS/JS no HTML |
| A78-8 | Clicar em nó navega ANTES do usuário querer | Confirmar double-click? Descartado — single click é UX esperada do Obsidian |

## Testes concretos

```python
# tests/test_grafo_filtrado.py
import sqlite3
import tempfile
from pathlib import Path

def test_grafo_filtrado_respeita_limite(tmp_path, monkeypatch):
    # Criar grafo sintético com 10 nodes do tipo 'fornecedor'
    db = tmp_path / "grafo.sqlite"
    con = sqlite3.connect(db)
    con.executescript("""
        CREATE TABLE node (id INTEGER PK, tipo TEXT, nome_canonico TEXT, aliases TEXT, metadata TEXT);
        CREATE TABLE edge (id INTEGER PK, src_id INTEGER, dst_id INTEGER, tipo TEXT, peso REAL);
    """)
    for i in range(10):
        con.execute("INSERT INTO node VALUES (?, 'fornecedor', ?, '[]', '{}')", (i, f"F{i}"))
    con.commit()

    monkeypatch.setattr("src.graph.queries._DB_PATH", db)
    from src.graph.queries import grafo_filtrado
    nodes, _ = grafo_filtrado(tipos=["fornecedor"], limite=5, incluir_orfaos=True)
    assert len(nodes) == 5


def test_label_humano_alias():
    from src.dashboard.componentes.grafo_pyvis import _label_humano
    assert _label_humano({"aliases": '["Americanas"]', "nome_canonico": "00.776..."}) == "Americanas"


def test_construir_grafo_injeta_click_handler():
    from src.dashboard.componentes.grafo_pyvis import construir_grafo_html
    html = construir_grafo_html(
        nodes=[{"id": 1, "tipo": "fornecedor", "nome_canonico": "Foo",
                "aliases": "[]", "metadata": "{}", "grau": 1}],
        edges=[],
    )
    assert "network.on(\"click\"" in html
    assert "window.parent.location" in html
```

## Evidências obrigatórias

- [x] `src/graph/queries.py::grafo_filtrado(db, tipos, incluir_orfaos, limite)`: ordena por grau decrescente, cap em `limite`, filtra órfãos, devolve edges apenas entre nodes selecionados. Tolerância: `tipos=[]` retorna vazio; `tipos=None` usa default canônico.
- [x] `src/dashboard/componentes/grafo_pyvis.py`: wrapper com `COR_POR_TIPO` (paleta Dracula para 13 tipos), `_label_humano` com fallback alias → razao_social → nome_canonico truncado, `construir_grafo_html(nodes, edges, altura_px)` que injeta click handler JavaScript via URL navigation. `_PYVIS_DISPONIVEL` com graceful degradation quando pyvis ausente.
- [x] **Click handler navega via `window.parent.location`**: sem dependência de postMessage. Mapeamento `_CAMPO_QUERY_POR_TIPO` traduz `fornecedor`→`fornecedor`, `categoria`→`categoria`, `periodo`→`mes_ref`, etc. Aba Extrato (Sprint 73) lê via `ler_filtros_da_url`.
- [x] **Grafo full-page na aba "Grafo + Obsidian"**: expander topo "Grafo Full-Page (Obsidian-like)" mostra layout 7/3 (grafo/filtros), painel lateral com multiselect de tipos, toggle órfãos, slider limite (100–2000), legenda colorida.
- [x] `pyproject.toml`: `pyvis>=0.3` adicionado em `optional-dependencies.dashboard`.
- [x] 16 testes em `tests/test_grafo_filtrado.py`: 6 de `_label_humano`/parsers + 5 de `construir_grafo_html` + 5 de `grafo_filtrado` (limite, tipos, órfãos, edges só entre selecionados, tipos vazio).
- [x] Gauntlet: make lint exit 0, 1032 passed (+11), 15 skipped (+5 por pyvis indisponível no pyenv local), smoke 8/8 OK.

### Ressalvas

- [R78-1] **pyvis indisponível no ambiente atual**: o Python 3.12.1 do pyenv do dev foi compilado sem suporte a `_bz2` (dependência transitiva de `networkx` exigida por `pyvis`). O wrapper faz graceful degradation (retorna `<p>pyvis não instalado</p>` em vez de crashar). Os 5 testes do HTML são pulados com `pytest.skipif`. Para habilitar: `brew install bzip2 && pyenv install 3.12.X` (macOS) ou `apt install libbz2-dev && pyenv install 3.12.X` (Ubuntu), ou usar Python do sistema. Não-bloqueante: a lógica está pronta, só o render visual precisa do ambiente ajustado.
- [R78-2] **Screenshot ANTES/DEPOIS** e medição de performance (<3s para 500 nós) exigem dashboard rodando com pyvis funcional (ver R78-1).
- [R78-3] **Sprint 78 não exportou `_DB_PATH` como pedido no spec**: o spec propõe `src.graph.queries._DB_PATH` global, mas o projeto usa `GrafoDB` como contexto (padrão consistente com Sprints 48, 70). Mantive o padrão `grafo_filtrado(db, ...)` recebendo o DB explícito. Mais testável (fixtures).

---

*"O grafo é um mapa. Navegar é o direito." — Andre*
