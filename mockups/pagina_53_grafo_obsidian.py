"""Página mockup -- Sprint 53 Grafo Visual + Obsidian Rico.

MOCKUP wireframe para Sprint 53 -- não é código de produção.
Três seções: grafo sintético, preview de MOC Obsidian, Sankey de fluxo.
"""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from mockups.tema_mockup import (
    CORES,
    LAYOUT_PLOTLY,
    badge_html,
    divisor,
    hero_titulo,
    rgba_cor,
    subtitulo_secao,
)

MOC_OBSIDIAN: str = """---
tipo: moc
mes: 2026-02
aliases:
  - "MOC Fevereiro 2026"
  - "2026-02"
tags:
  - moc
  - financeiro
  - mes-corrente
criado: 2026-03-01
atualizado: 2026-04-20
receita_total: 18432.77
despesa_total: 12987.43
saldo: 5445.34
documentos: 42
itens_catalogados: 187
---

# MOC — Fevereiro 2026

## Saldo do mes

- **Receita:** R$ 18.432,77
- **Despesa:** R$ 12.987,43
- **Saldo:** R$ 5.445,34 (+29,5%)

## Documentos chegados (42)

### DANFE (18)
- [[2026-02-03_DANFE_Americanas_NF-12389]] — R$ 287,40
- [[2026-02-08_DANFE_MagazineLuiza_NF-45021]] — R$ 1.289,00
- [[2026-02-12_DANFE_Neoenergia_NF-87732]] — R$ 498,67
- ...

### NFC-e (15)
- [[2026-02-05_NFCE_SuperMaia]] — R$ 412,89
- [[2026-02-11_NFCE_PadariaKiSabor]] — R$ 47,30
- ...

### Cupom termico (9)
- [[2026-02-04_Cupom_Farmacia]] — R$ 68,50
- [[2026-02-09_Cupom_PostoShell]] — R$ 189,72
- ...

## Top fornecedores

1. [[Fornecedor_Neoenergia]] — R$ 498,67 (1 doc)
2. [[Fornecedor_Americanas]] — R$ 287,40 (1 doc)
3. [[Fornecedor_MagazineLuiza]] — R$ 1.289,00 (1 doc)
4. [[Fornecedor_SuperMaia]] — R$ 1.847,23 (5 docs)

## Top categorias de item

- [[Categoria_Supermercado]] — R$ 2.187,43
- [[Categoria_Energia]] — R$ 498,67
- [[Categoria_Farmacia]] — R$ 187,40
- [[Categoria_Combustivel]] — R$ 542,18

## Alertas

- 3 documentos aguardando linking (ver [[Conferencia_2026-02]])
- Fatura [[Neoenergia]] 12% acima da media anual
- [[Item_Desodorante-Dove-150ml]] aparece 4x (possivel duplicidade)

## Conexoes

- [[MOC_2026-01]] (anterior)
- [[MOC_2026-03]] (proximo)
- [[Relatorio_Diagnostico_2026-02]]
- [[IRPF_2026]]

---

*Gerado automaticamente por src/obsidian/sync.py. Não editar manualmente.*
"""


def _renderizar_grafo() -> None:
    st.markdown(
        subtitulo_secao("Subgrafo interativo (exemplo: 1 documento)"),
        unsafe_allow_html=True,
    )
    nos_x = [0.5, 0.2, 0.8, 0.15, 0.35, 0.55, 0.75, 0.85, 0.5, 0.1]
    nos_y = [0.75, 0.55, 0.55, 0.25, 0.25, 0.25, 0.25, 0.55, 0.95, 0.75]
    nos_labels = [
        "DANFE 2026-02-08",
        "Americanas S.A.",
        "Transação Itaú<br>-R$ 287,40",
        "Item A<br>Tênis Nike",
        "Item B<br>Meia Lupo",
        "Item C<br>Mochila Urban",
        "Item D<br>Camiseta Dry",
        "Categoria<br>Vestuário",
        "Mês 2026-02",
        "Conta Itaú",
    ]
    nos_tipos = [
        "documento",
        "fornecedor",
        "transacao",
        "item",
        "item",
        "item",
        "item",
        "categoria",
        "periodo",
        "conta",
    ]
    cores_tipo = {
        "documento": CORES["destaque"],
        "fornecedor": CORES["alerta"],
        "transacao": CORES["neutro"],
        "item": CORES["positivo"],
        "categoria": CORES["superfluo"],
        "periodo": CORES["info"],
        "conta": CORES["texto_sec"],
    }
    nos_cores = [cores_tipo[t] for t in nos_tipos]
    nos_tamanhos = [40, 32, 30, 24, 24, 24, 24, 28, 26, 26]

    arestas = [
        (0, 1, "fornecido_por"),
        (0, 2, "linkado_a"),
        (0, 3, "contem_item"),
        (0, 4, "contem_item"),
        (0, 5, "contem_item"),
        (0, 6, "contem_item"),
        (3, 7, "categoria_de"),
        (4, 7, "categoria_de"),
        (5, 7, "categoria_de"),
        (6, 7, "categoria_de"),
        (0, 8, "ocorre_em"),
        (2, 9, "origem_em"),
    ]

    arestas_x: list[float | None] = []
    arestas_y: list[float | None] = []
    for origem, destino, _label in arestas:
        arestas_x += [nos_x[origem], nos_x[destino], None]
        arestas_y += [nos_y[origem], nos_y[destino], None]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=arestas_x,
            y=arestas_y,
            mode="lines",
            line={"width": 1.5, "color": rgba_cor(CORES["texto_sec"], 0.5)},
            hoverinfo="skip",
            showlegend=False,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=nos_x,
            y=nos_y,
            mode="markers+text",
            marker={
                "size": nos_tamanhos,
                "color": nos_cores,
                "line": {"color": CORES["texto"], "width": 2},
            },
            text=nos_labels,
            textposition="middle center",
            textfont={"size": 9, "color": CORES["fundo"]},
            hoverinfo="text",
            showlegend=False,
        )
    )
    fig.update_layout(
        **LAYOUT_PLOTLY,
        height=480,
        xaxis={
            "visible": False,
            "range": [-0.05, 1.05],
            "showgrid": False,
        },
        yaxis={
            "visible": False,
            "range": [0.1, 1.05],
            "showgrid": False,
        },
    )
    st.plotly_chart(fig, use_container_width=True)

    leg_cols = st.columns(len(cores_tipo))
    for col, (tipo, cor) in zip(leg_cols, cores_tipo.items()):
        with col:
            st.markdown(
                f'<div style="text-align: center;">{badge_html(tipo, cor, fonte_px=10)}</div>',
                unsafe_allow_html=True,
            )


def _renderizar_obsidian() -> None:
    st.markdown(
        subtitulo_secao("Obsidian Sync — preview do MOC 2026-02"),
        unsafe_allow_html=True,
    )
    col_a, col_b, col_c = st.columns(3)
    stats = [
        (col_a, "Notas geradas", "356", CORES["destaque"]),
        (col_b, "MOCs mensais", "12", CORES["neutro"]),
        (col_c, "Backlinks", "1.847", CORES["positivo"]),
    ]
    for col, label, valor, cor in stats:
        with col:
            st.markdown(
                f'<div style="'
                f"background-color: {CORES['card_fundo']};"
                f" border-radius: 10px;"
                f" padding: 14px 18px;"
                f' border-left: 3px solid {cor};">'
                f'<p style="color: {CORES["texto_sec"]};'
                f" font-size: 10px; font-weight: 600;"
                f' text-transform: uppercase; margin: 0;">{label}</p>'
                f'<p style="color: {cor};'
                f" font-size: 26px; font-weight: 700;"
                f' margin: 4px 0 0 0;">{valor}</p>'
                f"</div>",
                unsafe_allow_html=True,
            )

    st.markdown(
        f'<div style="'
        f"background-color: #1E1F29;"
        f" border-radius: 12px;"
        f" padding: 20px 24px;"
        f" margin-top: 16px;"
        f" max-height: 520px;"
        f" overflow-y: auto;"
        f" font-family: 'JetBrains Mono', monospace;"
        f" font-size: 12px;"
        f" line-height: 1.6;"
        f" color: {CORES['texto']};"
        f' border: 1px solid {rgba_cor(CORES["destaque"], 0.3)};">'
        f'<pre style="margin: 0; white-space: pre-wrap;'
        f" color: inherit; font-family: inherit;"
        f'">{MOC_OBSIDIAN}</pre>'
        f"</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        f'<p style="color: {CORES["texto_sec"]};'
        f" font-size: 11px; margin: 10px 0 0 0;"
        f' font-style: italic;">'
        "Caminho alvo: <code>$OBSIDIAN_VAULT/Ouroboros/Meses/2026-02.md</code>"
        " — gerado idempotentemente via template Jinja2."
        "</p>",
        unsafe_allow_html=True,
    )


def _renderizar_sankey() -> None:
    st.markdown(
        subtitulo_secao("Fluxo financeiro — Sankey (receita → categoria → fornecedor)"),
        unsafe_allow_html=True,
    )
    labels = [
        "Receita G4F",
        "Receita Infobase",
        "Moradia",
        "Alimentação",
        "Transporte",
        "Saúde",
        "Supérfluos",
        "Neoenergia",
        "Aluguel Ki-Sabor",
        "Super Maia",
        "Padaria Ki-Sabor",
        "Posto Shell",
        "Farmácia Pague Menos",
        "Americanas",
        "Magazine Luiza",
    ]
    cor_no = [
        CORES["positivo"],
        CORES["positivo"],
        CORES["destaque"],
        CORES["neutro"],
        CORES["alerta"],
        CORES["superfluo"],
        CORES["pink"] if "pink" in CORES else CORES["superfluo"],
        CORES["destaque"],
        CORES["destaque"],
        CORES["neutro"],
        CORES["neutro"],
        CORES["alerta"],
        CORES["superfluo"],
        CORES["info"],
        CORES["info"],
    ]
    origens = [0, 0, 0, 0, 1, 1, 1, 2, 2, 3, 3, 4, 5, 6, 6]
    destinos = [2, 3, 4, 6, 3, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]
    valores = [2500, 1800, 900, 600, 1200, 400, 500, 1800, 700, 1600, 200, 900, 400, 350, 150]

    fig = go.Figure(
        data=[
            go.Sankey(
                node={
                    "pad": 18,
                    "thickness": 18,
                    "line": {"color": CORES["texto_sec"], "width": 0.5},
                    "label": labels,
                    "color": cor_no,
                },
                link={
                    "source": origens,
                    "target": destinos,
                    "value": valores,
                    "color": [rgba_cor(CORES["texto_sec"], 0.25)] * len(valores),
                },
            )
        ]
    )
    fig.update_layout(**LAYOUT_PLOTLY, height=420)
    st.plotly_chart(fig, use_container_width=True)


def renderizar() -> None:
    """Ponto de entrada da pagina mockup 53."""
    st.markdown(
        hero_titulo(
            "53",
            "Grafo Visual + Obsidian Rico",
            "Visualização interativa do subgrafo de uma entidade, preview do "
            "MOC mensal sincronizado com Obsidian (frontmatter + wikilinks) "
            "e Sankey do fluxo receita-categoria-fornecedor.",
        ),
        unsafe_allow_html=True,
    )
    _renderizar_grafo()
    st.markdown(divisor(), unsafe_allow_html=True)
    _renderizar_obsidian()
    st.markdown(divisor(), unsafe_allow_html=True)
    _renderizar_sankey()


# "Conhecer é conectar." -- Heráclito (parafraseado)
