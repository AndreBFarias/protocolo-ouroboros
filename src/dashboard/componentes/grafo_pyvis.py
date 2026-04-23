"""Wrapper pyvis para renderizar o grafo Obsidian-like (Sprint 78).

O `construir_grafo_html(nodes, edges, altura_px)` monta uma `pyvis.Network`,
configura o layout de forças (Barnes-Hut), aplica tema Dracula e injeta um
click handler JavaScript que navega o iframe-pai para a aba Extrato filtrada.
Devolve o HTML como string — sem escrever arquivo no disco — pronto para
`st.components.v1.html()`.

Decisão arquitetural (ADR-19 + Sprint 78): a comunicação pyvis → Streamlit
usa URL navigation (`window.parent.location`) em vez de postMessage. É
robusta, funciona no mesmo origin do Streamlit, e a aba Extrato já lê
`st.query_params` desde a Sprint 73.
"""

from __future__ import annotations

import json
from typing import Any

try:
    from pyvis.network import Network

    _PYVIS_DISPONIVEL = True
except ImportError:  # pragma: no cover — dep opcional
    _PYVIS_DISPONIVEL = False
    Network = None  # type: ignore[assignment,misc]


# Paleta Dracula por tipo de nó (ADR-14 lista os 12 tipos canônicos).
COR_POR_TIPO: dict[str, str] = {
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
    "produto_canonico": "#50fa7b",
}

# Mapeia tipo do nó para o campo de query_param que a aba Extrato consome.
_CAMPO_QUERY_POR_TIPO: dict[str, str] = {
    "fornecedor": "fornecedor",
    "categoria": "categoria",
    "periodo": "mes_ref",
    "conta": "banco",
    "transacao": "local",  # heurística: Extrato tem busca por local
    "documento": "local",
    "item": "local",
}

_JS_CLICK_HANDLER_TEMPLATE = """
<script type="text/javascript">
  (function() {
    function anexarHandler() {
      if (typeof network === 'undefined' || !network) {
        return setTimeout(anexarHandler, 100);
      }
      network.on('click', function (params) {
        if (!params.nodes || params.nodes.length === 0) return;
        var nodeId = params.nodes[0];
        var node = nodes.get(nodeId);
        if (!node) return;
        var tipo = node.node_tipo || 'fornecedor';
        var nome = node.node_nome_canonico || node.label;
        var campo = __MAPA_CAMPOS__[tipo] || 'fornecedor';
        var url;
        try {
          url = new URL(window.parent.location.href);
        } catch (e) {
          url = new URL(window.location.href);
        }
        url.searchParams.set('tab', 'Extrato');
        url.searchParams.set(campo, nome);
        try {
          window.parent.location.href = url.toString();
        } catch (e) {
          window.location.href = url.toString();
        }
      });
    }
    anexarHandler();
  })();
</script>
"""


def _montar_js(mapa_campos: dict[str, str]) -> str:
    return _JS_CLICK_HANDLER_TEMPLATE.replace(
        "__MAPA_CAMPOS__", json.dumps(mapa_campos)
    )


def _parse_aliases(aliases: Any) -> list[str]:
    if not aliases:
        return []
    if isinstance(aliases, list):
        return [str(a) for a in aliases]
    if isinstance(aliases, str):
        try:
            parsed = json.loads(aliases)
            if isinstance(parsed, list):
                return [str(a) for a in parsed]
        except (ValueError, TypeError):
            pass
    return []


def _parse_metadata(metadata: Any) -> dict[str, Any]:
    if not metadata:
        return {}
    if isinstance(metadata, dict):
        return metadata
    if isinstance(metadata, str):
        try:
            parsed = json.loads(metadata)
            if isinstance(parsed, dict):
                return parsed
        except (ValueError, TypeError):
            pass
    return {}


def _label_humano(node: dict[str, Any]) -> str:
    """Fallback: aliases[0] → razao_social → descrição → tipo#id curto.

    P2.2 2026-04-23: quando nome_canonico é hash SHA-256 (caso transações e
    documentos), mostra `<tipo>#<id>` em vez do hash truncado.
    """
    aliases = _parse_aliases(node.get("aliases"))
    if aliases:
        return str(aliases[0])
    metadata = _parse_metadata(node.get("metadata"))
    for chave in ("razao_social", "nome_fantasia", "descricao"):
        if metadata.get(chave):
            return str(metadata[chave])
    nc = str(node.get("nome_canonico") or "")
    tipo = node.get("tipo")
    node_id = node.get("id", "?")
    # Hash SHA-256 tem 64 hex chars; se o nome canônico é hash-like, mostra
    # <tipo>#<id> que é mais legível ("transacao#4575" vs "5C277BC27E632...").
    if nc and len(nc) >= 32 and all(c in "0123456789abcdefABCDEF" for c in nc) and tipo:
        return f"{tipo}#{node_id}"
    if not nc:
        return f"node-{node_id}"
    return nc if len(nc) <= 40 else nc[:37] + "..."


def construir_grafo_html(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    altura_px: int = 800,
) -> str:
    """Renderiza o grafo como HTML standalone pronto para `st.components.v1.html`.

    - nodes: dicts com chaves `id, tipo, nome_canonico, aliases, metadata, grau`.
    - edges: dicts com chaves `src, dst, tipo, peso`.
    - altura_px: altura do canvas (Streamlit não auto-expande iframe).
    """
    if not _PYVIS_DISPONIVEL:
        return (
            "<p>pyvis não instalado. Rode <code>pip install pyvis</code>.</p>"
        )

    net = Network(
        height=f"{altura_px}px",
        width="100%",
        bgcolor="#282a36",
        font_color="#f8f8f2",
        directed=True,
        cdn_resources="in_line",
        notebook=False,
    )
    net.barnes_hut(
        gravity=-2000,
        central_gravity=0.3,
        spring_length=150,
        spring_strength=0.02,
    )
    net.set_options(
        json.dumps(
            {
                "interaction": {
                    "hover": True,
                    "tooltipDelay": 100,
                    "zoomView": True,
                    "dragView": True,
                },
                "physics": {"stabilization": {"iterations": 200}},
                "nodes": {
                    "font": {
                        "color": "#f8f8f2",
                        "size": 12,
                        "face": "monospace",
                    }
                },
                "edges": {
                    "color": {"color": "#6272a4", "highlight": "#bd93f9"},
                    "smooth": {"type": "dynamic"},
                },
            }
        )
    )

    for node in nodes:
        tipo = str(node.get("tipo", "fornecedor"))
        label = _label_humano(node)
        grau = int(node.get("grau") or 0)
        size = 10 + min(grau * 2, 40)
        tooltip = (
            f"<b>{tipo}</b><br>"
            f"{node.get('nome_canonico', '')}<br>"
            f"Conexões: {grau}"
        )
        net.add_node(
            node["id"],
            label=label[:30],
            color=COR_POR_TIPO.get(tipo, "#6272a4"),
            size=size,
            title=tooltip,
            node_tipo=tipo,
            node_nome_canonico=str(node.get("nome_canonico") or label),
        )

    for edge in edges:
        net.add_edge(
            edge["src"],
            edge["dst"],
            label=str(edge.get("tipo", ""))[:12],
            arrows={"to": {"enabled": True, "scaleFactor": 0.5}},
            width=max(0.5, float(edge.get("peso") or 1.0) * 1.5),
        )

    html = net.generate_html(notebook=False)
    # Injeta o JS do click handler antes de fechar o body.
    handler = _montar_js(_CAMPO_QUERY_POR_TIPO)
    html = html.replace("</body>", handler + "</body>")
    return html


# "O grafo é um mapa. Navegar é o direito." — Andre, Sprint 78
