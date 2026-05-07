"""Página Catalogação de Documentos -- Sprint UX-RD-09 (redesign sobre 51/126).

Reescrita visual da Catalogação espelhando o mockup
``novo-mockup/mockups/07-catalogacao.html``:

* ``page-header`` com título "CATALOGAÇÃO", subtítulo e ``sprint-tag UX-RD-09``;
* KPIs (4 cards) e cards por tipo preservados (UX-126 já validados);
* Toolbar redesign com glyph search + contagem mono;
* Tabela densa principal (.table do tema_css) com colunas mono e
  alinhamento tabular nos valores;
* Conflitos pendentes + Gaps de cobertura em ``st.columns([1, 1])``
  abaixo da tabela (UX-126 AC3 invariante).

Invariantes preservadas (testes regressivos UX-126/Sprint 51)
-------------------------------------------------------------
* ``COLUNAS_TABELA = ["Data", "Fornecedor", "Total", "Status"]`` -- 4
  colunas exatas; runtime check em ``_renderizar_tabela_documentos``.
* ``_page_header_html()`` é a moldura canônica UX-RD-09 (substitui
  ``hero_titulo_html`` legado — duplicação eliminada 2026-05-06).
* ``humanizar(tipo_tec)`` invocado em ``_renderizar_cards_por_tipo``
  (AC1 UX-126).
* ``_renderizar_tabela_documentos(docs)`` chamado com indentação 4
  espaços (largura total -- AC3 UX-126).
* ``st.columns([1, 1])`` envolve ``_renderizar_painel_conflitos`` e
  ``_renderizar_gaps`` (AC3 UX-126).
* Read-only sobre ``data/output/grafo.sqlite`` (modo ``ro``).
* Graceful degradation (ADR-10): grafo ausente mostra aviso e retorna.

Lições aplicadas
----------------
* UX-RD-04: HTML grande emitido via ``minificar()`` para evitar parser
  CommonMark interpretar indentação Python como bloco ``<pre><code>``.
* Cores via ``tema.CORES`` (nunca hardcode).
"""

from __future__ import annotations

import html as _html

import pandas as pd
import streamlit as st

from src.dashboard import dados as _dados
from src.dashboard.componentes.html_utils import minificar
from src.dashboard.componentes.humanizar_tipos import humanizar
from src.dashboard.componentes.ui import (
    callout_html,
    card_html,
    carregar_css_pagina,
    subtitulo_secao_html,
)
from src.dashboard.dados import (
    carregar_documentos_grafo,
    contar_propostas_linking,
    formatar_moeda,
)
from src.dashboard.tema import (
    CORES,
    FONTE_CORPO,
    FONTE_LABEL,
    FONTE_SUBTITULO,
    SPACING,
    rgba_cor_inline,
)

COLUNAS_TABELA: list[str] = ["Data", "Fornecedor", "Total", "Status"]

ROTULOS_TIPO_DOCUMENTO: dict[str, str] = {
    "nfe_modelo_55": "DANFE (NFe-55)",
    "nfce_modelo_65": "NFC-e (modelo 65)",
    "cupom_termico": "Cupom térmico",
    "cupom_garantia_estendida": "Garantia estendida",
    "receita_medica": "Receita médica",
    "garantia_fabricante": "Termo de garantia",
    "apolice_seguro": "Apólice de seguro",
    "documento_fiscal": "Documento fiscal",
    "irpf_parcela": "Parcela IRPF",
    "das_mei": "DAS MEI",
    "comprovante_cpf": "Comprovante CPF",
    "desconhecido": "Não identificado",
}

CORES_STATUS: dict[str, str] = {
    "Vinculado": CORES["positivo"],
    "Sem transação": CORES["alerta"],
    "Conflito": CORES["negativo"],
}


# ---------------------------------------------------------------------------
# CSS local da página -- redesign UX-RD-09 (toolbar + tabela densa)
# ---------------------------------------------------------------------------

# CSS dedicado da página: src/dashboard/css/paginas/catalogacao.css
# (UX-M-02.A-RESIDUAL extraiu de _CSS_LOCAL_CATALOGACAO inline.)


def renderizar(
    dados: dict[str, pd.DataFrame] | None = None,
    periodo: str | None = None,
    pessoa: str | None = None,
    ctx: dict | None = None,
) -> None:
    """Ponto de entrada da página Catalogação (UX-T-07)."""
    from src.dashboard.componentes.topbar_actions import renderizar_grupo_acoes
    renderizar_grupo_acoes([
        {"label": "Reprocessar", "glyph": "refresh",
         "title": "Re-extrair documentos"},
        {"label": "Adicionar tipo", "primary": True, "glyph": "plus",
         "title": "Cadastrar novo tipo de documento"},
    ])

    _ = dados, periodo, pessoa, ctx

    st.markdown(minificar(carregar_css_pagina("catalogacao")), unsafe_allow_html=True)

    # Page-header canônico UX-RD-09 (substitui hero_titulo_html legado
    # — duplicação visual eliminada 2026-05-06).
    if not _dados.CAMINHO_GRAFO.exists():
        st.markdown(_page_header_html(num_arquivos=0), unsafe_allow_html=True)
        st.markdown(
            callout_html(
                "warning",
                "Grafo SQLite não encontrado. Popule o catálogo rodando "
                "`./run.sh --tudo` (ou `make process`) para gerar "
                "`data/output/grafo.sqlite`.",
            ),
            unsafe_allow_html=True,
        )
        return

    docs = carregar_documentos_grafo()
    propostas_abertas = contar_propostas_linking()

    st.markdown(_page_header_html(num_arquivos=len(docs)), unsafe_allow_html=True)
    st.markdown(_toolbar_html(len(docs)), unsafe_allow_html=True)

    _renderizar_kpis(docs, propostas_abertas)
    st.markdown(_divisor(), unsafe_allow_html=True)
    _renderizar_cards_por_tipo(docs)
    st.markdown(_divisor(), unsafe_allow_html=True)

    # Sprint UX-126 AC3: layout vertical -- "Documentos Recentes" ocupa
    # 100% da largura; "Conflitos Pendentes" e "Gaps de Cobertura" ficam
    # lado-a-lado em st.columns([1, 1]) ABAIXO da tabela.
    _renderizar_tabela_documentos(docs)
    st.markdown(_divisor(), unsafe_allow_html=True)
    col_conflitos, col_gaps = st.columns([1, 1])
    with col_conflitos:
        _renderizar_painel_conflitos(docs)
    with col_gaps:
        _renderizar_gaps(docs)


# ---------------------------------------------------------------------------
# HTML helpers (page-header + toolbar UX-RD-09)
# ---------------------------------------------------------------------------


def _page_header_html(num_arquivos: int) -> str:
    """HTML do page-header UX-RD-09 (título + subtítulo + sprint-tag)."""
    pill_html = (
        f'<span class="pill pill-d7-graduado">{num_arquivos} arquivos</span>'
        if num_arquivos
        else ""
    )
    return minificar(
        f"""
        <div class="page-header">
          <div>
            <h1 class="page-title">CATALOGAÇÃO</h1>
            <p class="page-subtitle">
              Banco de dados normalizado. Cada arquivo é canônico pelo
              sha256; documentos são vinculados a transações via grafo
              SQLite (status: vinculado, sem transação, conflito).
            </p>
          </div>
          <div class="page-meta">
            <span class="sprint-tag">UX-RD-09</span>
            {pill_html}
          </div>
        </div>
        """
    )


def _toolbar_html(num_arquivos: int) -> str:
    """HTML da toolbar redesign (glyph search + contagem mono)."""
    return minificar(
        f"""
        <div class="ouroboros-cat-toolbar">
          <span class="icon">&#x2315;</span>
          <span class="label">
            Catálogo normalizado por sha256 — visão tabular densa,
            ordenada por data descendente, top 20 mais recentes.
          </span>
          <span class="ct">{num_arquivos} no catálogo</span>
        </div>
        """
    )


# ---------------------------------------------------------------------------
# KPIs e cards por tipo
# ---------------------------------------------------------------------------


def _renderizar_kpis(docs: pd.DataFrame, propostas: int) -> None:
    """Cards de KPI: total, chegaram no mês, % vinculados, propostas abertas."""
    total_docs = len(docs)

    mes_atual = _mes_atual_str()
    if not docs.empty and "data_emissao" in docs.columns:
        docs_mes = int(docs["data_emissao"].fillna("").str.startswith(mes_atual).sum())
    else:
        docs_mes = 0

    if total_docs > 0:
        vinculados = int((docs["status_linking"] == "Vinculado").sum())
        pct_linked = vinculados / total_docs
    else:
        pct_linked = 0.0

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(
            card_html("Documentos catalogados", str(total_docs), CORES["destaque"]),
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            card_html("Chegaram este mês", str(docs_mes), CORES["neutro"]),
            unsafe_allow_html=True,
        )
    with col3:
        cor_pct = CORES["positivo"] if pct_linked >= 0.7 else CORES["alerta"]
        st.markdown(
            card_html("Vinculados a transação", f"{pct_linked:.0%}", cor_pct),
            unsafe_allow_html=True,
        )
    with col4:
        cor_props = CORES["alerta"] if propostas > 0 else CORES["texto_sec"]
        st.markdown(
            card_html("Propostas abertas", str(propostas), cor_props),
            unsafe_allow_html=True,
        )


def _renderizar_cards_por_tipo(docs: pd.DataFrame) -> None:
    """Cards pequenos por tipo de documento com contagem."""
    st.markdown(
        subtitulo_secao_html("Documentos por tipo"),
        unsafe_allow_html=True,
    )

    if docs.empty:
        st.markdown(
            callout_html("info", "Nenhum documento catalogado ainda."),
            unsafe_allow_html=True,
        )
        return

    contagem = docs["tipo_documento"].value_counts().to_dict()

    paleta = [
        CORES["destaque"],
        CORES["neutro"],
        CORES["alerta"],
        CORES["info"],
        CORES["superfluo"],
        CORES["positivo"],
        CORES["questionavel"],
    ]

    tipos_ordenados = sorted(contagem.items(), key=lambda kv: kv[1], reverse=True)
    cols = st.columns(max(len(tipos_ordenados), 1))

    for idx, (tipo_tec, qtd) in enumerate(tipos_ordenados):
        cor = paleta[idx % len(paleta)]
        # Sprint UX-126 AC1: humanizar slug do tipo. Override legado em
        # ROTULOS_TIPO_DOCUMENTO ainda tem prioridade (nomes mais elaborados
        # como "DANFE (NFe-55)"); fallback para mapping YAML + Title Case.
        rotulo = ROTULOS_TIPO_DOCUMENTO.get(tipo_tec) or humanizar(tipo_tec)
        with cols[idx]:
            st.markdown(
                _card_tipo_html(rotulo, int(qtd), cor),
                unsafe_allow_html=True,
            )


# ---------------------------------------------------------------------------
# Tabela de documentos
# ---------------------------------------------------------------------------


def _renderizar_tabela_documentos(docs: pd.DataFrame) -> None:
    """Tabela com 4 colunas: Data, Fornecedor, Total, Status.

    UX-RD-09: além do ``st.dataframe`` canônico (preservado para o
    contrato runtime e exportação CSV), uma faixa HTML densa com 7
    colunas mono é renderizada acima como visualização redesign do
    mockup ``07-catalogacao.html`` (sha8 + tipo + fornecedor + mês +
    doc? + valor + pessoa).
    """
    st.markdown(
        subtitulo_secao_html("Documentos recentes"),
        unsafe_allow_html=True,
    )

    if docs.empty:
        st.markdown(
            callout_html("info", "Nenhum documento para exibir."),
            unsafe_allow_html=True,
        )
        return

    docs_ordenados = docs.sort_values("data_emissao", ascending=False).head(20)

    # ---- Faixa HTML densa redesign (7 colunas mono) ---------------------
    st.markdown(_tabela_densa_html(docs_ordenados), unsafe_allow_html=True)

    # ---- DataFrame canônico (4 colunas, contrato runtime) ---------------
    tabela = pd.DataFrame(
        {
            "Data": docs_ordenados["data_emissao"].fillna("--"),
            "Fornecedor": docs_ordenados["razao_social"].fillna("").replace("", "--").str.title(),
            "Total": docs_ordenados["total"].apply(
                lambda v: formatar_moeda(v) if v and v > 0 else "--"
            ),
            "Status": docs_ordenados["status_linking"],
        }
    )

    colunas_efetivas = list(tabela.columns)
    if colunas_efetivas != COLUNAS_TABELA:
        raise RuntimeError(f"Colunas da tabela divergem do contrato: {colunas_efetivas}")

    st.dataframe(
        tabela,
        width="stretch",
        hide_index=True,
        column_config={
            "Data": st.column_config.TextColumn("Data", width="small"),
            "Fornecedor": st.column_config.TextColumn("Fornecedor", width="large"),
            "Total": st.column_config.TextColumn("Total", width="small"),
            "Status": st.column_config.TextColumn("Status", width="small"),
        },
    )


def _tabela_densa_html(docs: pd.DataFrame) -> str:
    """Renderiza tabela densa redesign (7 colunas mono) em HTML.

    Colunas: sha8 | tipo | fornecedor | mês | doc? | valor | pessoa.
    Usa classe ``.table`` do tema_css UX-RD-02 (sticky thead, mono em
    valores, alinhamento tabular).
    """
    if docs.empty:
        return ""

    linhas: list[str] = []
    for _, row in docs.iterrows():
        sha = str(row.get("sha8", "") or row.get("sha256", "") or "--")[:8] or "--"
        tipo_tec = str(row.get("tipo_documento", "--"))
        tipo_label = ROTULOS_TIPO_DOCUMENTO.get(tipo_tec) or humanizar(tipo_tec) or "--"
        forn = str(row.get("razao_social", "") or "--").strip() or "--"
        forn = forn.title() if forn != "--" else "--"
        data_e = str(row.get("data_emissao", "") or "--")
        mes = data_e[:7] if data_e and data_e != "--" else "--"
        status = str(row.get("status_linking", "--"))
        # "Doc?" no contexto da catalogação representa: tem transação
        # vinculada? Quando vinculado => marca verde (entidade unicode
        # CHECK MARK escapada via &#x2713;); senão traço.
        check = (
            "<span style='color:var(--accent-green);'>"
            "&#x2713;</span>"
            if status == "Vinculado"
            else "<span style='color:var(--text-muted);'>—</span>"
        )
        total_v = float(row.get("total", 0.0) or 0.0)
        total_str = formatar_moeda(total_v) if total_v else "--"
        pessoa = str(row.get("quem", "") or row.get("pessoa", "") or "--").strip() or "--"

        # Pill colorido para tipo (cores do CORES_STATUS quando Status é
        # conhecido; senão neutro).
        cor_status = CORES_STATUS.get(status, CORES["texto_sec"])
        pill_status = (
            f"<span class='pill' style='border-color:{cor_status};"
            f" color:{cor_status}; font-size:10px;'>{_html.escape(status)}</span>"
        )
        linhas.append(
            "<tr>"
            f"<td class='col-mono'>{_html.escape(sha)}</td>"
            f"<td class='col-mono'>{_html.escape(tipo_label)}</td>"
            f"<td>{_html.escape(forn)}</td>"
            f"<td class='col-mono'>{_html.escape(mes)}</td>"
            f"<td class='col-num'>{check}</td>"
            f"<td class='col-num'>{_html.escape(total_str)}</td>"
            f"<td class='col-mono'>{_html.escape(pessoa)} {pill_status}</td>"
            "</tr>"
        )

    cabecalho = (
        "<tr>"
        "<th>sha8</th>"
        "<th>Tipo</th>"
        "<th>Fornecedor</th>"
        "<th>Mês</th>"
        "<th>Doc?</th>"
        "<th>Valor</th>"
        "<th>Pessoa</th>"
        "</tr>"
    )
    return minificar(
        f"""
        <div style="background: var(--bg-surface);
                    border: 1px solid var(--border-subtle);
                    border-radius: 10px;
                    overflow: hidden;
                    margin-bottom: 12px;">
          <table class="table">
            <thead>{cabecalho}</thead>
            <tbody>{"".join(linhas)}</tbody>
          </table>
        </div>
        """
    )


# ---------------------------------------------------------------------------
# Conflitos pendentes + Gaps de cobertura
# ---------------------------------------------------------------------------


def _renderizar_painel_conflitos(docs: pd.DataFrame) -> None:
    """Lista propostas abertas em docs/propostas/linking/."""
    st.markdown(
        subtitulo_secao_html("Conflitos pendentes", cor=CORES["alerta"]),
        unsafe_allow_html=True,
    )

    if not _dados.CAMINHO_PROPOSTAS_LINKING.exists():
        st.markdown(
            callout_html("info", "Diretório de propostas de linking ainda não existe."),
            unsafe_allow_html=True,
        )
        return

    arquivos = sorted(
        _dados.CAMINHO_PROPOSTAS_LINKING.glob("*.md"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    if not arquivos:
        st.markdown(
            callout_html("success", "Nenhum conflito de linking pendente."),
            unsafe_allow_html=True,
        )
        return

    for arq in arquivos[:10]:
        severidade = _severidade_proposta(arq.name)
        cor = {
            "alta": CORES["negativo"],
            "media": CORES["alerta"],
            "baixa": CORES["texto_sec"],
        }[severidade]

        st.markdown(
            _card_conflito_html(arq.name, severidade, cor, str(arq)),
            unsafe_allow_html=True,
        )

    _ = docs


def _renderizar_gaps(docs: pd.DataFrame) -> None:
    """Lista meses com menos de 5 documentos catalogados."""
    st.markdown(
        subtitulo_secao_html("Gaps de cobertura", cor=CORES["negativo"]),
        unsafe_allow_html=True,
    )

    if docs.empty or "data_emissao" not in docs.columns:
        st.markdown(
            callout_html("info", "Sem dados de cobertura."),
            unsafe_allow_html=True,
        )
        return

    docs_com_data = docs[docs["data_emissao"].fillna("") != ""].copy()
    if docs_com_data.empty:
        st.markdown(
            callout_html("info", "Documentos sem data de emissão."),
            unsafe_allow_html=True,
        )
        return

    docs_com_data["mes_ref"] = docs_com_data["data_emissao"].str[:7]
    por_mes = docs_com_data["mes_ref"].value_counts().to_dict()

    gaps = [(mes, qtd) for mes, qtd in por_mes.items() if qtd < 5]
    gaps.sort(key=lambda x: x[0], reverse=True)

    if not gaps:
        st.markdown(
            callout_html("success", "Todos os meses com >=5 documentos."),
            unsafe_allow_html=True,
        )
        return

    for mes, qtd in gaps[:8]:
        st.markdown(
            _card_gap_html(mes, int(qtd)),
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Helpers diversos
# ---------------------------------------------------------------------------


def _severidade_proposta(nome_arquivo: str) -> str:
    """Heurística simples: palavras-chave no nome indicam severidade."""
    nome = nome_arquivo.lower()
    if "conflito" in nome or "duplo" in nome or "ambigu" in nome:
        return "alta"
    if "threshold" in nome or "ocr" in nome or "baixa" in nome:
        return "media"
    return "baixa"


def _mes_atual_str() -> str:
    """YYYY-MM do mês atual."""
    from datetime import date

    return date.today().strftime("%Y-%m")


def _divisor() -> str:
    """HTML de um divisor horizontal fino."""
    return (
        f'<hr style="'
        f"border: 0;"
        f" border-top: 1px solid {rgba_cor_inline(CORES['texto_sec'], 0.25)};"
        f" margin: {SPACING['lg']}px 0;"
        f'" />'
    )


def _card_tipo_html(rotulo: str, contagem: int, cor: str) -> str:
    """Card pequeno de tipo de documento."""
    return (
        f'<div style="'
        f"background-color: {CORES['card_fundo']};"
        f" border-radius: 10px;"
        f" padding: {SPACING['md'] - 2}px {SPACING['sm'] + 4}px;"
        f" border-top: 3px solid {cor};"
        f" text-align: center;"
        f' min-height: 120px;">'
        f'<p style="color: {CORES["texto_sec"]};'
        f" font-size: {FONTE_LABEL}px;"
        f" font-weight: 600;"
        f" line-height: 1.3;"
        f' margin: 0 0 {SPACING["sm"] + 2}px 0;">{rotulo}</p>'
        f'<p style="color: {cor};'
        f" font-size: 28px;"
        f" font-weight: 700;"
        f" line-height: 1;"
        f' margin: 0;">{contagem}</p>'
        f"</div>"
    )


def _card_conflito_html(nome: str, severidade: str, cor: str, caminho: str) -> str:
    """Card de conflito pendente.

    Sprint 92c: classe ``.ouroboros-row-between`` consolida o cabecalho
    (nome + chip de severidade). Wrapper preserva div inline porque
    border-left varia por severidade.
    """
    return (
        '<div style="background-color: var(--color-card-fundo);'
        " border-radius: 10px;"
        f" padding: {SPACING['sm'] + 4}px {SPACING['md']}px;"
        f" margin-bottom: {SPACING['sm'] + 2}px;"
        f' border-left: 3px solid {cor};">'
        '<div class="ouroboros-row-between"'
        f' style="align-items: center; margin-bottom: {SPACING["xs"]}px;">'
        '<p style="color: var(--color-texto);'
        f" font-size: {FONTE_CORPO}px;"
        " font-weight: 600;"
        " margin: 0;"
        f' word-break: break-all;">{nome}</p>'
        f'<span style="background-color: {cor};'
        " color: var(--color-fundo);"
        " border-radius: 4px;"
        " padding: 2px 6px;"
        f" font-size: {FONTE_LABEL - 2}px;"
        " font-weight: 700;"
        " text-transform: uppercase;"
        f' margin-left: {SPACING["sm"]}px;">{severidade}</span>'
        "</div>"
        '<p style="color: var(--color-neutro);'
        f" font-size: {FONTE_LABEL - 1}px;"
        " font-family: monospace;"
        f' margin: 0;">{caminho}</p>'
        "</div>"
    )


def _card_gap_html(mes: str, contagem: int) -> str:
    """Card horizontal de gap de cobertura.

    Sprint 92c: classe ``.ouroboros-row-between`` consolida o layout
    horizontal; cores migram para ``var(--color-*)``.
    """
    return (
        '<div class="ouroboros-row-between"'
        ' style="background-color: var(--color-card-fundo);'
        " border-radius: 10px;"
        f" padding: {SPACING['sm'] + 4}px {SPACING['md']}px;"
        f" margin-bottom: {SPACING['sm']}px;"
        ' align-items: center;">'
        '<div><p style="color: var(--color-texto);'
        f" font-size: {FONTE_CORPO}px;"
        " font-weight: 600;"
        f' margin: 0;">{mes}</p>'
        '<p style="color: var(--color-texto-sec);'
        f" font-size: {FONTE_LABEL - 1}px;"
        ' margin: 2px 0 0 0;">esperado: 5+</p></div>'
        '<div style="text-align: right;">'
        '<p style="color: var(--color-negativo);'
        f" font-size: {FONTE_SUBTITULO + 4}px;"
        " font-weight: 700;"
        f' margin: 0; line-height: 1;">{contagem}</p>'
        '<p style="color: var(--color-texto-sec);'
        f" font-size: {FONTE_LABEL - 2}px;"
        ' margin: 2px 0 0 0;">docs</p></div>'
        "</div>"
    )


# "Catalogar é o primeiro ato da inteligência." -- parafraseado de Carl Linnaeus
