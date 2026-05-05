"""Página de extrato detalhado (UX-RD-06: tabela densa + breakdown + drawer).

Reescrita da página Extrato seguindo o mockup ``novo-mockup/mockups/02-extrato.html``:

* **Saldo no topo**: card grande mono 32px tabular-nums + 3 mini-KPIs do
  período (Receita, Despesa, Transações count).
* **Tabela densa** (.table do tema_css.py UX-RD-02): row-h 32px, sticky
  thead, mono em valor/data, alinhamento tabular nos valores, hover/selected.
* **Breakdown lateral por categoria**: top 5 categorias em barras
  proporcionais (1fr direita contra 2.5fr da tabela).
* **Drawer JSON syntax-highlighted**: clicar uma linha (via selectbox +
  botão "Abrir drawer") mostra o JSON da transação no painel lateral
  com cores --syn-key/string/number/bool/null.

Lições aplicadas
----------------
* UX-RD-04: HTML grande (tabela com N linhas, breakdown, drawer) emitido
  via ``minificar()`` para evitar que o parser CommonMark interprete a
  indentação Python como bloco ``<pre><code>``.
* Sprint 73 (drill-down) preservada: ``_aplicar_drilldown`` + breadcrumb.
* Sprint 87.2 (tracking documental): coluna ``Doc?`` continua funcionando
  via ``_marcar_tracking`` + grafo SQLite.
* Sprint 92a.8 (paginação 25 linhas): mantida.
* Filtros (``filtrar_por_periodo``, ``filtrar_por_pessoa``,
  ``filtrar_por_forma_pagamento``) e exportação CSV: preservados.

Decisão drawer (Streamlit não tem drawer nativo)
------------------------------------------------
Optamos por HTML absolute-positioned via ``st.markdown(..., unsafe_allow_html=True)``
controlado por ``st.session_state["extrato_drawer_idx"]``. O drawer é
renderizado depois da tabela (no DOM) mas vai para a direita via
``position: fixed`` do CSS de UX-RD-02. Botão "Fechar" emite ``st.button``
que limpa o estado e dá rerun. Trade-off: drawer ocupa espaço da tabela em
viewport estreito; em widescreen fica ao lado, espelhando o mockup.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st
import yaml

from src.dashboard.componentes.drawer_transacao import (
    renderizar_drawer,
    transacao_para_dict,
)
from src.dashboard.componentes.drilldown import (
    filtros_ativos_do_session_state,
    limpar_filtro,
)
from src.dashboard.componentes.html_utils import minificar
from src.dashboard.dados import (
    filtrar_por_forma_pagamento,
    filtrar_por_periodo,
    filtrar_por_pessoa,
    filtro_forma_ativo,
)
from src.dashboard.tema import (
    CORES,
    FONTE_CORPO,
    breadcrumb_drilldown_html,
    callout_html,
    hero_titulo_html,
    icon_html,
)

# Sprint 73: mapeamento dos filtros vindos de drill-down para colunas do DF.
_MAPA_FILTRO_COLUNA: dict[str, str] = {
    "mes": "mes_ref",
    "mes_ref": "mes_ref",
    "categoria": "categoria",
    "classificacao": "classificacao",
    "fornecedor": "local",  # fuzzy contains, case-insensitive
    "local": "local",
    "banco": "banco_origem",
    "banco_origem": "banco_origem",
    "forma": "forma_pagamento",
    "forma_pagamento": "forma_pagamento",
}


_CAMINHO_CATEGORIAS_TRACKING: Path = (
    Path(__file__).resolve().parents[3] / "mappings" / "categorias_tracking.yaml"
)

TAMANHO_PAGINA_EXTRATO: int = 25
"""Sprint 92a.8: número de linhas por página na tabela do Extrato."""

_CHAVE_DRAWER_IDX = "extrato_drawer_idx"


# ---------------------------------------------------------------------------
# Helpers (drilldown, tracking documental)
# ---------------------------------------------------------------------------


def _aplicar_drilldown(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, str]]:
    """Aplica filtros vindos de drill-down (Sprint 73). Retorna df filtrado
    e dict dos filtros efetivos aplicados (para breadcrumb)."""
    filtros = filtros_ativos_do_session_state()
    aplicados: dict[str, str] = {}
    for campo, valor in filtros.items():
        coluna = _MAPA_FILTRO_COLUNA.get(campo)
        if not coluna or coluna not in df.columns:
            continue
        if campo in ("fornecedor", "local"):
            mascara = (
                df[coluna]
                .fillna("")
                .astype(str)
                .str.contains(valor, case=False, na=False, regex=False)
            )
            df = df[mascara]
        else:
            df = df[df[coluna].astype(str) == valor]
        aplicados[campo] = valor
    return df, aplicados


def _renderizar_breadcrumb(filtros: dict[str, str]) -> None:
    """Exibe breadcrumb com X para remover cada filtro ativo (Sprint 73)."""
    if not filtros:
        return
    st.markdown(
        breadcrumb_drilldown_html(filtros),
        unsafe_allow_html=True,
    )
    cols = st.columns(len(filtros))
    for i, (campo, _valor) in enumerate(filtros.items()):
        with cols[i]:
            if st.button(
                f"× remover {campo}",
                key=f"limpar_filtro_{campo}",
                use_container_width=True,
            ):
                limpar_filtro(campo)
                st.rerun()


@lru_cache(maxsize=1)
def _carregar_categorias_obrigatorias() -> frozenset[str]:
    """Lê `mappings/categorias_tracking.yaml` uma vez e cacheia em memória."""
    if not _CAMINHO_CATEGORIAS_TRACKING.exists():
        return frozenset()
    try:
        dados = yaml.safe_load(_CAMINHO_CATEGORIAS_TRACKING.read_text(encoding="utf-8"))
    except (yaml.YAMLError, OSError):
        return frozenset()
    lista = (dados or {}).get("obrigatoria_tracking", []) or []
    return frozenset(str(c) for c in lista)


def _marcar_tracking(
    row: pd.Series,
    obrigatorias: frozenset[str],
    ids_com_doc: set[str],
) -> str:
    """Sprint 87.2 (ADR-20): devolve o marcador da coluna "Doc?" do Extrato."""
    ident = row.get("identificador") if hasattr(row, "get") else None
    if ident is not None and not pd.isna(ident):
        ident_str = str(ident)
        if ident_str and ident_str in ids_com_doc:
            return "Doc ok"
    categoria = row.get("categoria", "") if hasattr(row, "get") else ""
    return "Faltando" if categoria in obrigatorias else ""


@st.cache_data(ttl=30)
def _carregar_ids_com_doc() -> set[str]:
    """Sprint 87.2 (ADR-20): transações do grafo com documento vinculado."""
    try:
        from src.graph.db import GrafoDB, caminho_padrao
        from src.graph.queries import transacoes_com_documento
    except ImportError:  # pragma: no cover -- módulo de grafo ausente no dev local
        return set()

    try:
        db_path = caminho_padrao()
        if not db_path.exists():
            return set()
        with GrafoDB(db_path) as db:
            return transacoes_com_documento(db)
    except Exception:  # noqa: BLE001 -- dashboard nunca deve quebrar por grafo ausente
        return set()


# ---------------------------------------------------------------------------
# Cálculos (saldo topo, breakdown lateral)
# ---------------------------------------------------------------------------


def calcular_saldo_topo(df: pd.DataFrame) -> dict[str, float]:
    """Calcula saldo, receita, despesa e count para o card de topo.

    Convenção: ``valor`` negativo é despesa, positivo é receita. ``tipo``
    "Transferência Interna" é excluído de ambos para não inflar nem somas
    nem perdas.
    """
    if df.empty:
        return {"saldo": 0.0, "receita": 0.0, "despesa": 0.0, "transacoes": 0}

    if "tipo" in df.columns:
        operacional = df[df["tipo"].astype(str) != "Transferência Interna"]
    else:
        operacional = df

    valores = pd.to_numeric(operacional.get("valor"), errors="coerce").fillna(0.0)
    receita = float(valores[valores > 0].sum())
    despesa = float(valores[valores < 0].sum())  # já negativo
    saldo = receita + despesa  # despesa é negativa
    return {
        "saldo": saldo,
        "receita": receita,
        "despesa": despesa,  # negativo
        "transacoes": int(len(df)),
    }


def calcular_breakdown_categorias(df: pd.DataFrame, top_n: int = 5) -> list[dict[str, Any]]:
    """Top-N categorias por valor absoluto de despesa.

    Retorna lista ordenada decrescente de dicts ``{categoria, valor, pct}``
    onde ``valor`` é o total absoluto de despesas (positivo) e ``pct`` é
    a proporção (0..100) sobre o total.
    """
    if df.empty or "categoria" not in df.columns:
        return []

    if "tipo" in df.columns:
        operacional = df[df["tipo"].astype(str) != "Transferência Interna"]
    else:
        operacional = df

    valores = pd.to_numeric(operacional.get("valor"), errors="coerce").fillna(0.0)
    apenas_despesas = operacional[valores < 0].copy()
    apenas_despesas["__abs"] = (-valores[valores < 0]).values

    if apenas_despesas.empty:
        return []

    agrupado = (
        apenas_despesas.groupby("categoria", dropna=False)["__abs"]
        .sum()
        .sort_values(ascending=False)
        .head(top_n)
    )
    total = float(agrupado.sum())
    if total <= 0:
        return []

    resultado: list[dict[str, Any]] = []
    for categoria, valor in agrupado.items():
        cat = str(categoria) if not pd.isna(categoria) else "Sem categoria"
        resultado.append(
            {
                "categoria": cat,
                "valor": float(valor),
                "pct": float(valor) / total * 100.0,
            }
        )
    return resultado


# ---------------------------------------------------------------------------
# HTML builders
# ---------------------------------------------------------------------------


def _formatar_brl(valor: float) -> str:
    sinal = "-" if valor < 0 else ""
    return f"{sinal}R$ {abs(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _saldo_topo_html(metricas: dict[str, float], periodo_rotulo: str) -> str:
    """Card grande de saldo + 3 mini-KPIs (receita, despesa, count)."""
    saldo = metricas["saldo"]
    receita = metricas["receita"]
    despesa = metricas["despesa"]  # negativo
    n = int(metricas["transacoes"])

    cor_saldo = CORES["positivo"] if saldo >= 0 else CORES["negativo"]

    return minificar(
        f"""
        <div class="extrato-saldo-topo">
            <div class="extrato-saldo-card">
                <span class="extrato-saldo-rotulo">SALDO · {periodo_rotulo}</span>
                <span class="extrato-saldo-valor" style="color:{cor_saldo};">
                    {_formatar_brl(saldo)}
                </span>
                <span class="extrato-saldo-meta">
                    {n} transações no período
                </span>
            </div>
            <div class="extrato-saldo-mini">
                <div class="extrato-mini-kpi">
                    <span class="extrato-mini-rotulo">RECEITA</span>
                    <span class="extrato-mini-valor" style="color:{CORES['positivo']};">
                        {_formatar_brl(receita)}
                    </span>
                </div>
                <div class="extrato-mini-kpi">
                    <span class="extrato-mini-rotulo">DESPESA</span>
                    <span class="extrato-mini-valor" style="color:{CORES['negativo']};">
                        {_formatar_brl(despesa)}
                    </span>
                </div>
                <div class="extrato-mini-kpi">
                    <span class="extrato-mini-rotulo">TRANSAÇÕES</span>
                    <span class="extrato-mini-valor">{n}</span>
                </div>
            </div>
        </div>
        """
    )


def _tabela_densa_html(df: pd.DataFrame, idx_drawer: int | None = None) -> str:
    """Emite ``<table class="table">`` com as linhas do DF.

    Cada linha é gerada como uma única string concatenada (sem indentação
    interna) e o conjunto é minificado antes do retorno. Isso evita que o
    parser CommonMark veja indentação ≥ 4 e renderize ``<pre><code>``.
    """
    if df.empty:
        return minificar(
            """
            <p class="extrato-vazio">Sem transações para exibir nesta página.</p>
            """
        )

    # Formatação leve de cada coluna.
    linhas: list[str] = []
    for ord_idx, (_real_idx, row) in enumerate(df.iterrows()):
        data_v = row.get("data")
        if data_v is None or pd.isna(data_v):
            data_str = "-"
        else:
            data_str = pd.to_datetime(data_v).strftime("%Y-%m-%d")

        valor = float(pd.to_numeric(row.get("valor"), errors="coerce") or 0.0)
        cor_val = CORES["negativo"] if valor < 0 else CORES["positivo"]
        valor_str = _formatar_brl(valor)

        descricao = str(row.get("local") or "-")
        if len(descricao) > 48:
            descricao = descricao[:45] + "..."

        categoria = str(row.get("categoria") or "-")
        forma = str(row.get("forma_pagamento") or "-")
        quem = str(row.get("quem") or "-")

        # Marcador "Doc?" — vem de _marcar_tracking se a coluna existir
        tracking = str(row.get("__tracking", "") or "")
        if tracking == "Doc ok":
            doc_cell = (
                '<span class="extrato-doc-ok" title="Documento vinculado no grafo">'
                "+</span>"
            )
        elif tracking == "Faltando":
            doc_cell = (
                '<span class="extrato-doc-faltando" '
                'title="Categoria obrigatória sem comprovante">!</span>'
            )
        else:
            doc_cell = '<span class="extrato-doc-vazio">·</span>'

        classe_linha = "selected" if (idx_drawer is not None and idx_drawer == ord_idx) else ""

        linha = (
            f'<tr class="{classe_linha}">'
            f'<td class="col-mono">{data_str}</td>'
            f'<td class="col-desc">{_escape(descricao)}</td>'
            f'<td><span class="extrato-pill-cat">{_escape(categoria)}</span></td>'
            f'<td class="col-num" style="color:{cor_val};">{valor_str}</td>'
            f'<td class="col-mono">{_escape(forma)}</td>'
            f'<td><span class="extrato-pill-pessoa">{_escape(quem)}</span></td>'
            f'<td class="col-doc">{doc_cell}</td>'
            f"</tr>"
        )
        linhas.append(linha)

    cabecalho = (
        '<thead><tr>'
        '<th>Data</th>'
        '<th>Descrição</th>'
        '<th>Categoria</th>'
        '<th class="col-num">Valor</th>'
        '<th>Forma</th>'
        '<th>Pessoa</th>'
        '<th>Doc?</th>'
        "</tr></thead>"
    )
    corpo = "<tbody>" + "".join(linhas) + "</tbody>"
    return minificar(
        f'<div class="extrato-tabela-wrap"><table class="table">{cabecalho}{corpo}</table></div>'
    )


def _escape(texto: str) -> str:
    """Escape mínimo para evitar quebra de tags via < ou > em descrição."""
    return (
        texto.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _breakdown_lateral_html(top_categorias: list[dict[str, Any]]) -> str:
    """Card lateral com top-N categorias em barras horizontais."""
    if not top_categorias:
        return minificar(
            """
            <div class="extrato-breakdown">
                <span class="extrato-breakdown-titulo">BREAKDOWN POR CATEGORIA</span>
                <p class="extrato-breakdown-vazio">Sem despesas no período.</p>
            </div>
            """
        )

    # Paleta cíclica reusando tokens existentes.
    paleta = [
        "var(--accent-purple)",
        "var(--accent-pink)",
        "var(--accent-cyan)",
        "var(--accent-green)",
        "var(--accent-yellow)",
    ]

    barras: list[str] = []
    for i, item in enumerate(top_categorias):
        cor = paleta[i % len(paleta)]
        nome = _escape(item["categoria"])
        valor = _formatar_brl(item["valor"])
        pct = item["pct"]
        barra = (
            f'<div class="extrato-cat-barra">'
            f'<div class="extrato-cat-linha">'
            f'<span class="extrato-cat-nome">'
            f'<span class="extrato-cat-dot" style="background:{cor};"></span>'
            f"{nome}"
            f"</span>"
            f'<span class="extrato-cat-valor">{valor}</span>'
            f"</div>"
            f'<div class="extrato-cat-track">'
            f'<span style="width:{pct:.1f}%; background:{cor};"></span>'
            f"</div>"
            f'<span class="extrato-cat-pct">{pct:.0f}%</span>'
            f"</div>"
        )
        barras.append(barra)

    return minificar(
        '<div class="extrato-breakdown">'
        '<span class="extrato-breakdown-titulo">'
        "BREAKDOWN · TOP 5 CATEGORIAS"
        "</span>"
        + "".join(barras)
        + "</div>"
    )


def _estilos_locais_html() -> str:
    """CSS específico da página Extrato (componentes não previstos em
    UX-RD-02 ficam aqui para não estourar o tema_css.py).
    """
    return minificar(
        """
        <style>
        /* Saldo no topo */
        .extrato-saldo-topo {
            display: grid;
            grid-template-columns: 2fr 3fr;
            gap: var(--sp-4);
            margin-bottom: var(--sp-4);
        }
        .extrato-saldo-card {
            background: var(--bg-surface);
            border: 1px solid var(--border-subtle);
            border-radius: var(--r-md);
            padding: var(--sp-4) var(--sp-5);
            display: flex;
            flex-direction: column;
            gap: var(--sp-2);
        }
        .extrato-saldo-rotulo {
            font-family: var(--ff-mono);
            font-size: var(--fs-11);
            letter-spacing: 0.10em;
            text-transform: uppercase;
            color: var(--text-muted);
        }
        .extrato-saldo-valor {
            font-family: var(--ff-mono);
            font-size: 32px;
            font-weight: 500;
            font-variant-numeric: tabular-nums;
            line-height: 1.1;
        }
        .extrato-saldo-meta {
            font-family: var(--ff-mono);
            font-size: var(--fs-11);
            color: var(--text-muted);
        }
        .extrato-saldo-mini {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: var(--sp-3);
        }
        .extrato-mini-kpi {
            background: var(--bg-surface);
            border: 1px solid var(--border-subtle);
            border-radius: var(--r-md);
            padding: var(--sp-3) var(--sp-4);
            display: flex;
            flex-direction: column;
            gap: var(--sp-1);
        }
        .extrato-mini-rotulo {
            font-family: var(--ff-mono);
            font-size: var(--fs-11);
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: var(--text-muted);
        }
        .extrato-mini-valor {
            font-family: var(--ff-mono);
            font-size: 18px;
            font-weight: 500;
            font-variant-numeric: tabular-nums;
        }

        /* Layout principal */
        .extrato-grid {
            display: grid;
            grid-template-columns: 2.5fr 1fr;
            gap: var(--sp-4);
            margin-top: var(--sp-3);
        }

        /* Tabela densa */
        .extrato-tabela-wrap {
            background: var(--bg-surface);
            border: 1px solid var(--border-subtle);
            border-radius: var(--r-md);
            overflow: hidden;
            max-height: 70vh;
            overflow-y: auto;
        }
        .extrato-pill-cat {
            font-family: var(--ff-mono);
            font-size: var(--fs-11);
            padding: 2px 6px;
            border-radius: var(--r-xs);
            background: var(--bg-inset);
            color: var(--text-secondary);
            border: 1px solid var(--border-subtle);
        }
        .extrato-pill-pessoa {
            font-family: var(--ff-mono);
            font-size: var(--fs-11);
            padding: 2px 6px;
            border-radius: var(--r-full);
            background: var(--bg-inset);
            color: var(--text-secondary);
            border: 1px solid var(--border-subtle);
        }
        .extrato-doc-ok {
            color: var(--accent-green);
            font-family: var(--ff-mono);
            font-weight: 700;
        }
        .extrato-doc-faltando {
            color: var(--accent-orange);
            font-family: var(--ff-mono);
            font-weight: 700;
        }
        .extrato-doc-vazio { color: var(--text-muted); }
        .col-desc {
            color: var(--text-secondary);
            max-width: 320px;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .col-doc { text-align: center; }
        .extrato-vazio {
            padding: var(--sp-4);
            color: var(--text-muted);
            font-family: var(--ff-mono);
            font-size: var(--fs-12);
        }
        .extrato-info-pagina {
            color: var(--accent-purple);
            font-size: var(--fs-13);
            font-weight: 500;
            margin: 10px 0;
        }

        /* Breakdown lateral */
        .extrato-breakdown {
            background: var(--bg-surface);
            border: 1px solid var(--border-subtle);
            border-radius: var(--r-md);
            padding: var(--sp-4);
            display: flex;
            flex-direction: column;
            gap: var(--sp-3);
        }
        .extrato-breakdown-titulo {
            font-family: var(--ff-mono);
            font-size: var(--fs-11);
            letter-spacing: 0.10em;
            text-transform: uppercase;
            color: var(--text-secondary);
            border-bottom: 1px solid var(--border-subtle);
            padding-bottom: var(--sp-2);
        }
        .extrato-breakdown-vazio {
            color: var(--text-muted);
            font-size: var(--fs-12);
        }
        .extrato-cat-barra {
            display: flex;
            flex-direction: column;
            gap: 4px;
        }
        .extrato-cat-linha {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: var(--fs-12);
        }
        .extrato-cat-nome {
            font-family: var(--ff-mono);
            color: var(--text-primary);
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }
        .extrato-cat-dot {
            width: 8px; height: 8px; border-radius: 2px; display: inline-block;
        }
        .extrato-cat-valor {
            font-family: var(--ff-mono);
            font-variant-numeric: tabular-nums;
            color: var(--text-secondary);
        }
        .extrato-cat-track {
            height: 4px;
            background: var(--bg-inset);
            border-radius: var(--r-full);
            overflow: hidden;
        }
        .extrato-cat-track > span {
            display: block; height: 100%;
        }
        .extrato-cat-pct {
            font-family: var(--ff-mono);
            font-size: 10px;
            color: var(--text-muted);
            align-self: flex-end;
        }

        /* Drawer JSON detalhe */
        .drawer-json {
            background: var(--bg-inset);
            border: 1px solid var(--border-subtle);
            border-radius: var(--r-sm);
            padding: var(--sp-3);
            font-family: var(--ff-mono);
            font-size: var(--fs-12);
            line-height: 1.5;
            color: var(--text-primary);
            margin: 0 0 var(--sp-3);
            overflow-x: auto;
            white-space: pre;
        }
        .drawer-titulo {
            font-family: var(--ff-mono);
            font-size: var(--fs-11);
            letter-spacing: 0.10em;
            text-transform: uppercase;
            color: var(--text-secondary);
        }
        .drawer-hint {
            font-family: var(--ff-mono);
            font-size: 10px;
            color: var(--text-muted);
        }
        .drawer-doc, .drawer-doc-vazio {
            border-top: 1px solid var(--border-subtle);
            padding-top: var(--sp-3);
            display: flex;
            flex-direction: column;
            gap: 4px;
            font-size: var(--fs-12);
        }
        .drawer-doc-rotulo {
            font-family: var(--ff-mono);
            font-size: var(--fs-11);
            letter-spacing: 0.10em;
            text-transform: uppercase;
            color: var(--text-muted);
            margin-bottom: var(--sp-1);
        }
        .drawer-doc-linha {
            display: flex;
            gap: var(--sp-2);
            align-items: baseline;
        }
        .drawer-doc-chave {
            font-family: var(--ff-mono);
            color: var(--text-muted);
            min-width: 80px;
        }
        .drawer-doc-valor {
            font-family: var(--ff-mono);
            background: var(--bg-elevated);
            padding: 2px 6px;
            border-radius: var(--r-xs);
        }
        .drawer-doc-msg {
            color: var(--text-muted);
            font-size: var(--fs-12);
        }
        </style>
        """
    )


# ---------------------------------------------------------------------------
# Função pública
# ---------------------------------------------------------------------------


def renderizar(
    dados: dict[str, pd.DataFrame],
    mes_selecionado: str,
    pessoa: str,
    ctx: dict | None = None,
) -> None:
    """Renderiza a página de extrato (UX-RD-06).

    Mantém assinatura intocada para que ``app.py`` continue chamando
    ``renderizar(dados, periodo, pessoa, ctx)`` sem mudança.
    """
    st.markdown(_estilos_locais_html(), unsafe_allow_html=True)
    st.markdown(
        hero_titulo_html(
            "",
            "Extrato",
            "Tabela densa com transações do período, breakdown por categoria "
            "e drawer detalhado com JSON syntático e documento vinculado.",
        ),
        unsafe_allow_html=True,
    )

    if "extrato" not in dados:
        st.markdown(
            callout_html("warning", "Nenhum dado encontrado para o extrato."),
            unsafe_allow_html=True,
        )
        return

    gran = ctx.get("granularidade", "Mês") if ctx else "Mês"
    periodo = ctx.get("periodo", mes_selecionado) if ctx else mes_selecionado

    extrato = dados["extrato"]
    df = filtrar_por_periodo(extrato, gran, periodo)
    df = filtrar_por_pessoa(df, pessoa)
    df = filtrar_por_forma_pagamento(df, filtro_forma_ativo())
    # Sprint 73 (ADR-19): aplica filtros vindos de drill-down.
    df, filtros_drilldown = _aplicar_drilldown(df)
    _renderizar_breadcrumb(filtros_drilldown)

    if df.empty:
        st.markdown(
            callout_html("info", "Sem transações para o período selecionado."),
            unsafe_allow_html=True,
        )
        return

    # ---------- Saldo no topo ----------
    metricas_topo = calcular_saldo_topo(df)
    rotulo_periodo = str(periodo) if periodo else "período"
    st.markdown(
        _saldo_topo_html(metricas_topo, rotulo_periodo),
        unsafe_allow_html=True,
    )

    # ---------- Filtros locais (busca + avançados) ----------
    busca = st.text_input(
        "Buscar por local",
        key="busca_local",
        placeholder="Digite para filtrar...",
    )

    with st.expander("Filtros avançados", expanded=False):
        col1, col2 = st.columns(2)

        with col1:
            categorias = ["Todas"] + sorted(df["categoria"].dropna().unique().tolist())
            categoria_sel = st.selectbox("Categoria", categorias, key="avancado_categoria")

            bancos = ["Todos"] + sorted(df["banco_origem"].dropna().unique().tolist())
            banco_sel = st.selectbox("Banco", bancos, key="avancado_banco")

        with col2:
            classificacoes = ["Todas"] + sorted(df["classificacao"].dropna().unique().tolist())
            classificacao_sel = st.selectbox(
                "Classificação",
                classificacoes,
                key="avancado_classificacao",
            )

            tipos = ["Todos"] + sorted(df["tipo"].dropna().unique().tolist())
            tipo_sel = st.selectbox("Tipo", tipos, key="avancado_tipo")

    resultado = df.copy()

    if busca.strip():
        mascara = resultado["local"].fillna("").str.contains(busca.strip(), case=False, na=False)
        resultado = resultado[mascara]

    if categoria_sel != "Todas":
        resultado = resultado[resultado["categoria"] == categoria_sel]

    if classificacao_sel != "Todas":
        resultado = resultado[resultado["classificacao"] == classificacao_sel]

    if banco_sel != "Todos":
        resultado = resultado[resultado["banco_origem"] == banco_sel]

    if tipo_sel != "Todos":
        resultado = resultado[resultado["tipo"] == tipo_sel]

    # Sprint 87.2: tracking documental — coluna oculta usada pela tabela HTML.
    obrigatorias = _carregar_categorias_obrigatorias()
    if obrigatorias and "categoria" in resultado.columns:
        ids_com_doc = _carregar_ids_com_doc()
        resultado = resultado.copy()
        resultado["__tracking"] = resultado.apply(
            lambda row: _marcar_tracking(row, obrigatorias, ids_com_doc),
            axis=1,
        ).values

    # ---------- Layout: tabela (esquerda) + breakdown (direita) ----------
    breakdown = calcular_breakdown_categorias(resultado)
    _exibir_layout(resultado, breakdown)

    # ---------- Exportação CSV ----------
    _exibir_exportacao(resultado)

    # ---------- Drawer (renderizado quando idx setado) ----------
    _exibir_drawer(resultado)


def _exibir_layout(df: pd.DataFrame, breakdown: list[dict[str, Any]]) -> None:
    """Layout 2.5fr (tabela paginada) + 1fr (breakdown) via st.columns."""
    total = len(df)
    if total == 0:
        st.markdown(
            callout_html("info", "Nenhuma transação após filtros."),
            unsafe_allow_html=True,
        )
        return

    tamanho = TAMANHO_PAGINA_EXTRATO
    n_paginas = max(1, (total + tamanho - 1) // tamanho)

    col_info, col_pag = st.columns([3, 1])
    with col_pag:
        pagina = st.selectbox(
            "Página",
            options=list(range(1, n_paginas + 1)),
            index=0,
            key="extrato_pagina",
            label_visibility="collapsed",
        )

    inicio, fim = _calcular_slice_pagina(total, tamanho, int(pagina))

    with col_info:
        st.markdown(
            f'<p class="extrato-info-pagina">'
            f"Mostrando {inicio + 1}-{fim} de {total} transações</p>",
            unsafe_allow_html=True,
        )

    df_pagina = df.iloc[inicio:fim]

    # Sprint 92c: legenda educativa da coluna ``Doc?`` (preservada após
    # migração para tabela HTML densa em UX-RD-06). Usa ``icon_html`` para
    # renderizar Feather inline (check-circle / alert-triangle) e mantém os
    # rótulos PT-BR ``Doc ok`` / ``Faltando`` para casar com o contrato de
    # ``_marcar_tracking``.
    icone_ok = icon_html("check-circle", tamanho=14, cor=CORES["positivo"])
    icone_falt = icon_html("alert-triangle", tamanho=14, cor=CORES["alerta"])
    legenda_doc_html = minificar(
        f"""
        <p class="extrato-legenda-doc" style="color:{CORES['texto_sec']};
            font-size:{FONTE_CORPO}px; margin: 4px 0 12px 0;">
            Coluna 'Doc?':
            <span style="color:{CORES['positivo']};">{icone_ok} Doc ok</span>
            = documento vinculado no grafo;
            <span style="color:{CORES['alerta']};">{icone_falt} Faltando</span>
            = categoria obrigatória sem comprovante; vazio = sem tracking.
        </p>
        """
    )

    idx_drawer = st.session_state.get(_CHAVE_DRAWER_IDX)
    idx_drawer_pagina: int | None = None
    if idx_drawer is not None:
        try:
            idx_int = int(idx_drawer)
            if inicio <= idx_int < fim:
                idx_drawer_pagina = idx_int - inicio
        except (TypeError, ValueError):
            idx_drawer_pagina = None

    col_tabela, col_breakdown = st.columns([2.5, 1])
    with col_tabela:
        st.markdown(
            _tabela_densa_html(df_pagina, idx_drawer=idx_drawer_pagina),
            unsafe_allow_html=True,
        )
        st.markdown(legenda_doc_html, unsafe_allow_html=True)
    with col_breakdown:
        st.markdown(
            _breakdown_lateral_html(breakdown),
            unsafe_allow_html=True,
        )

    # Seletor + botão "Abrir drawer" (compromisso pragmático Streamlit).
    rotulos = _rotulos_transacoes(df_pagina)
    if rotulos:
        col_sel, col_btn = st.columns([4, 1])
        with col_sel:
            sel_local = st.selectbox(
                "Inspecionar transação",
                options=list(range(len(rotulos))),
                format_func=lambda i: rotulos[i] if i < len(rotulos) else "",
                key="extrato_seletor_drawer",
            )
        with col_btn:
            st.write("")
            if st.button("Abrir drawer", key="extrato_btn_drawer", type="primary"):
                # Converte índice da página para índice global no df filtrado.
                idx_global = inicio + int(sel_local)
                st.session_state[_CHAVE_DRAWER_IDX] = idx_global


def _rotulos_transacoes(df: pd.DataFrame) -> list[str]:
    """Rótulos curtos para o selectbox de inspeção."""
    rotulos: list[str] = []
    for _, row in df.iterrows():
        data_v = row.get("data")
        data_str = (
            pd.to_datetime(data_v).strftime("%Y-%m-%d")
            if data_v is not None and not pd.isna(data_v)
            else "-"
        )
        valor = float(pd.to_numeric(row.get("valor"), errors="coerce") or 0.0)
        local = str(row.get("local") or "")[:40]
        rotulos.append(f"{data_str} · R$ {valor:,.2f} · {local}")
    return rotulos


def _exibir_exportacao(df: pd.DataFrame) -> None:
    """Botão de download CSV (preserva contrato Sprint 92)."""
    if df.empty:
        return
    colunas_export = [
        c
        for c in [
            "data",
            "valor",
            "local",
            "categoria",
            "classificacao",
            "forma_pagamento",
            "banco_origem",
            "tipo",
            "quem",
            "mes_ref",
        ]
        if c in df.columns
    ]
    csv = "﻿" + df[colunas_export].to_csv(index=False, sep=";", decimal=",")
    st.download_button(
        label="Exportar CSV",
        data=csv,
        file_name="extrato.csv",
        mime="text/csv",
    )


def _exibir_drawer(df: pd.DataFrame) -> None:
    """Renderiza o drawer JSON quando ``session_state`` tem índice setado."""
    idx = st.session_state.get(_CHAVE_DRAWER_IDX)
    if idx is None:
        return
    try:
        idx_int = int(idx)
    except (TypeError, ValueError):
        return
    if idx_int < 0 or idx_int >= len(df):
        # índice obsoleto (filtro mudou); limpa silenciosamente.
        del st.session_state[_CHAVE_DRAWER_IDX]
        return

    row = df.iloc[idx_int]
    transacao = transacao_para_dict(row)

    # Documento vinculado pelo grafo (best-effort).
    doc_vinculado = _buscar_doc_vinculado(row)

    drawer_html = renderizar_drawer(transacao, doc_vinculado)
    st.markdown(drawer_html, unsafe_allow_html=True)

    if st.button("Fechar drawer", key="extrato_btn_fechar_drawer"):
        del st.session_state[_CHAVE_DRAWER_IDX]
        st.rerun()


def _buscar_doc_vinculado(row: pd.Series) -> dict[str, Any] | None:
    """Best-effort: busca primeiro documento vinculado à transação no grafo.

    Não há ainda função canônica ``documentos_de_transacao`` em
    ``src/graph/queries.py``; o caminho atual (UX-RD-06) checa apenas se o
    ``identificador`` da transação está no conjunto de transações com
    documento vinculado e devolve um stub mínimo. Quando uma sprint futura
    adicionar a query rica, basta substituir o corpo desta função.
    """
    ident = row.get("identificador") if hasattr(row, "get") else None
    if ident is None or pd.isna(ident):
        return None
    try:
        ids_com_doc = _carregar_ids_com_doc()
    except Exception:  # noqa: BLE001
        return None
    if str(ident) not in ids_com_doc:
        return None
    return {
        "sha8": str(ident)[:8],
        "tipo_edge_semantico": "documento_de",
        "nome": "ver módulo de Documentos",
    }


def _calcular_slice_pagina(
    total_linhas: int, tamanho_pagina: int, pagina_1_based: int
) -> tuple[int, int]:
    """Sprint 92a.8: devolve ``(start, stop)`` 0-indexado para ``iloc``."""
    if total_linhas <= 0 or tamanho_pagina <= 0:
        return (0, 0)
    n_paginas = max(1, (total_linhas + tamanho_pagina - 1) // tamanho_pagina)
    pagina = max(1, min(pagina_1_based, n_paginas))
    inicio = (pagina - 1) * tamanho_pagina
    fim = min(inicio + tamanho_pagina, total_linhas)
    return (inicio, fim)


# "O dinheiro é um bom servo, mas um mau mestre." -- Francis Bacon
